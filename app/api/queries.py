"""
Query and RAG API routes
"""
import logging
import hashlib
import json
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import uuid4

from app.schemas.query import (
    QueryRequest, QueryResponse, QueryHistory, QueryFeedback,
    RAGRequest, RAGResponse, ContextDocument, QueryAnalytics
)
from app.dependencies import (
    CurrentUserDep, DatabaseDep,
    VectorServiceDep, LLMServiceDep, EmbeddingServiceDep, CacheServiceDep
)
from app.models.query import Query, QueryResponse as QueryResponseModel
from app.database.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queries", tags=["Queries & RAG"])


@router.get("/debug/vector-status")
async def debug_vector_status(
    current_user: CurrentUserDep,
    vector_service: VectorServiceDep
):
    """
    Debug endpoint to check vector store status
    """
    try:
        # Check collection status
        collection_exists = await vector_service.init_collection()
        
        # Get collection info
        from qdrant_client.http import models
        # Use default collection from vector service
        collection_info = await vector_service.async_client.get_collection(vector_service.default_collection)
        
        # Count documents for this user
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=str(current_user.id))
                )
            ]
        )
        
        # Get document count
        scroll_result = await vector_service.async_client.scroll(
            collection_name=vector_service.default_collection,
            scroll_filter=search_filter,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        documents = scroll_result[0] if scroll_result else []
        
        return {
            "collection_exists": collection_exists,
            "total_vectors": collection_info.vectors_count,
            "user_documents": len(documents),
            "user_id": str(current_user.id),
            "sample_documents": [
                {
                    "id": doc.id,
                    "document_id": doc.payload.get("document_id"),
                    "source": doc.payload.get("source", "")[:50] + "..." if doc.payload.get("source") else None
                }
                for doc in documents[:5]  # Show first 5 documents
            ]
        }
        
    except Exception as e:
        logger.error(f"Debug vector status failed: {e}")
        return {
            "error": str(e),
            "collection_exists": False,
            "user_documents": 0
        }


@router.get("/debug/search-test")
async def debug_search_test(
    query: str = "test",
    max_chunks: int = 5,
    score_threshold: float = 0.3,
    current_user: CurrentUserDep = None,
    vector_service: VectorServiceDep = None,
    embedding_service: EmbeddingServiceDep = None,
    cache: CacheServiceDep = None
):
    """
    Debug endpoint to test search functionality
    """
    try:
        # Generate embedding for the query
        query_embedding = await embedding_service.embed_text(query)
        
        # Stable, per-user cache key
        q_norm = (query or "").strip()
        q_hash = hashlib.sha256(q_norm.encode("utf-8")).hexdigest()
        cache_key = f"search:user:{current_user.id}:{q_hash}:{max_chunks}:{score_threshold}"
        cached = cache.get_json(cache_key)
        if cached is not None:
            search_results = cached
            logger.info(f"Search cache hit: user={current_user.id} query='{query}' results={len(search_results)}")
        else:
            # Perform search
            search_results = await vector_service.search_documents(
                user_id=str(current_user.id),
                query_embedding=query_embedding,
                limit=max_chunks,
                score_threshold=score_threshold,
                filter_conditions=None
            )
            cache.set_json(cache_key, search_results, ttl_seconds=120)
            logger.info(f"Search cache miss: set user={current_user.id} query='{query}' results={len(search_results)}")
        
        return {
            "query": query,
            "user_id": str(current_user.id),
            "embedding_dimension": len(query_embedding),
            "score_threshold": score_threshold,
            "results_found": len(search_results),
            "results": search_results[:3] if search_results else [],  # Show first 3 results
            "all_scores": [r.get("score", 0) for r in search_results] if search_results else []
        }
        
    except Exception as e:
        logger.error(f"Debug search test failed: {e}")
        return {
            "error": str(e),
            "query": query,
            "results_found": 0
        }


@router.post("/rag", response_model=RAGResponse)
async def generate_rag_response(
    rag_request: RAGRequest,
    current_user: CurrentUserDep,
    db: DatabaseDep,
    vector_service: VectorServiceDep,
    llm_service: LLMServiceDep,
    embedding_service: EmbeddingServiceDep,
    cache: CacheServiceDep
):
    """
    Generate RAG response with retrieved context
    """
    start_time = time.time()
    
    try:
        start_time = time.time()
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(rag_request.query)
        try:
            emb_len = len(query_embedding) if isinstance(query_embedding, list) else 0
        except Exception:
            emb_len = 0
        logger.info(f"RAG: generated query embedding length={emb_len}")
        
        # Build filter conditions for document retrieval
        filter_conditions = {}
        if rag_request.document_ids:
            # Convert UUIDs to strings for filtering
            filter_conditions["document_id"] = [str(doc_id) for doc_id in rag_request.document_ids]
        
        # Retrieve relevant documents from vector store with cache + auto-relax threshold
        base_threshold = rag_request.score_threshold if rag_request.score_threshold is not None else 0.3
        thresholds_to_try = [base_threshold]
        if base_threshold > 0.0:
            thresholds_to_try.append(0.1)
            thresholds_to_try.append(0.0)
        
        search_results = []
        chosen_threshold = base_threshold
        rq_norm = (rag_request.query or "").strip()
        rq_hash = hashlib.sha256(rq_norm.encode("utf-8")).hexdigest()
        filt_key = (
            json.dumps(rag_request.document_ids and [str(d) for d in rag_request.document_ids] or [], sort_keys=True)
            if rag_request.document_ids else "none"
        )
        for thr in thresholds_to_try:
            cache_key = f"search:user:{current_user.id}:{rq_hash}:{rag_request.max_chunks}:{thr}:{filt_key}"
            cached = cache.get_json(cache_key)
            if cached is not None:
                search_results = cached
                chosen_threshold = thr
                logger.info(f"RAG search cache hit: user={current_user.id} thr={thr} results={len(search_results)}")
            else:
                # Perform search
                search_results = await vector_service.search_documents(
                    user_id=str(current_user.id),
                    query_embedding=query_embedding,
                    limit=rag_request.max_chunks,
                    score_threshold=thr,
                    filter_conditions=filter_conditions
                )
                cache.set_json(cache_key, search_results, ttl_seconds=120)
                logger.info(f"RAG search cache miss: set user={current_user.id} thr={thr} results={len(search_results)}")
                chosen_threshold = thr
            logger.info(f"RAG: retrieved {len(search_results) if search_results else 0} chunks for user={current_user.id} at threshold={thr}")
            if search_results:
                break
        if not search_results and base_threshold > 0.0:
            logger.info(f"RAG: no chunks found even after relaxing threshold for user={current_user.id}")
        
        # Format context documents
        context_documents = []
        context_text_parts = []
        
        for result in search_results:
            context_doc = ContextDocument(
                chunk_id=str(result["id"]) if result["id"] else str(uuid4()),
                document_id=str(result["document_id"]) if result["document_id"] else str(uuid4()),
                score=result["score"],
                text=result["text"],
                source=result.get("source") or result.get("metadata", {}).get("filename") or "Unknown",
                page_number=result.get("page_number"),
                chunk_index=result["chunk_index"],
                doc_metadata=result["metadata"]
            )
            context_documents.append(context_doc)
            context_text_parts.append(result["text"])
        
        # Prepare context for LLM
        context_used = "\n\n".join(context_text_parts)
        
        # Use user's LLM configuration if not specified
        # Note: current_user has llm_provider/llm_model in per-user mode
        llm_provider = rag_request.llm_provider or getattr(current_user, "llm_provider", None) or "anthropic"
        llm_model = rag_request.llm_model or getattr(current_user, "llm_model", None) or "claude-3-5-sonnet-20241022"
        logger.info(f"RAG: using provider={llm_provider}, model={llm_model}")
        
        # Cache-aware LLM response
        context_ids = ",".join([str(doc.chunk_id) for doc in context_documents]) if context_documents else "none"
        llm_cache_key = f"llm:user:{current_user.id}:{llm_provider}:{llm_model}:{rq_hash}:{context_ids}:{chosen_threshold}:{rag_request.max_tokens}:{rag_request.temperature}"
        llm_cached = cache.get_json(llm_cache_key)
        if llm_cached is not None:
            logger.info(f"LLM cache hit: user={current_user.id} model={llm_model}")
            class Resp:  # lightweight adapter
                def __init__(self, data):
                    self.content = data.get("content", "")
                    self.usage = data.get("usage", {})
            llm_response = Resp(llm_cached)
        else:
            # Generate LLM response
            llm_response = await llm_service.generate_rag_response(
                query=rag_request.query,
                context_documents=[doc.dict() for doc in context_documents],
                provider=llm_provider,
                model=llm_model,
                system_prompt=rag_request.system_prompt,
                temperature=rag_request.temperature,
                max_tokens=rag_request.max_tokens,
                stream=False  # Non-streaming for this endpoint
            )
            cache.set_json(llm_cache_key, {"content": llm_response.content, "usage": llm_response.usage}, ttl_seconds=300)
            logger.info(f"LLM cache miss: set user={current_user.id} model={llm_model}")
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create query record
        query_record = Query(
            user_id=current_user.id,
            query_text=rag_request.query,
            query_type="rag",
            processing_time_ms=processing_time,
            status="completed",
            retrieved_chunks_count=len(context_documents),
            retrieved_documents=[str(doc.document_id) for doc in context_documents],
            similarity_threshold=rag_request.score_threshold,
            llm_provider=llm_provider,
            llm_model=llm_model,
            input_tokens=llm_response.usage.get("prompt_tokens", 0),
            output_tokens=llm_response.usage.get("completion_tokens", 0),
            total_tokens=llm_response.usage.get("total_tokens", 0),
            estimated_cost=0.0,  # Would calculate based on provider pricing
            session_id=rag_request.session_id,
            conversation_turn=rag_request.conversation_turn,
            query_metadata={"rag_request": rag_request.model_dump(mode='json')}
        )
        
        db.add(query_record)
        db.commit()
        db.refresh(query_record)
        
        # Create response record
        response_record = QueryResponseModel(
            query_id=query_record.id,
            response_text=llm_response.content,
            response_format="text",
            context_used=context_used,
            context_chunks=[str(doc.chunk_id) for doc in context_documents],
            confidence_score=None,  # Could be calculated based on retrieval scores
            source_attribution=[doc.source for doc in context_documents],
            contains_citations=False,  # Could be analyzed
            fact_checked=False
        )
        
        db.add(response_record)
        db.commit()
        
        # Build response
        rag_response = RAGResponse(
            query_id=query_record.id,
            query=rag_request.query,
            response=llm_response.content,
            context_documents=context_documents,
            context_used=context_used,
            processing_time_ms=processing_time,
            llm_provider=llm_provider,
            llm_model=llm_model,
            input_tokens=llm_response.usage.get("prompt_tokens", 0),
            output_tokens=llm_response.usage.get("completion_tokens", 0),
            total_tokens=llm_response.usage.get("total_tokens", 0),
            estimated_cost=0.0,
            confidence_score=None,
            source_attribution=list(set(doc.source for doc in context_documents)),
            contains_citations=False,
            session_id=rag_request.session_id,
            conversation_turn=rag_request.conversation_turn,
            created_at=query_record.created_at
        )
        
        logger.info(f"RAG query completed for user {current_user.email}: {query_record.id}")
        return rag_response
        
    except Exception as e:
        # Log full traceback for better diagnostics
        logger.exception(f"RAG query failed: {e}")
        
        # Record failed query
        try:
            failed_query = Query(
                user_id=current_user.id,
                query_text=rag_request.query,
                query_type="rag",
                processing_time_ms=(time.time() - start_time) * 1000,
                status="failed",
                query_metadata={"error": str(e), "rag_request": rag_request.model_dump(mode='json')}
            )
            db.add(failed_query)
            db.commit()
        except:
            pass  # Don't fail twice
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG query failed"
        )


@router.post("/rag/stream")
async def generate_rag_response_stream(
    rag_request: RAGRequest,
    current_user: CurrentUserDep,
    db: DatabaseDep,
    vector_service: VectorServiceDep,
    llm_service: LLMServiceDep,
    embedding_service: EmbeddingServiceDep
):
    """
    Generate streaming RAG response
    """
    try:
        start_time = time.time()
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(rag_request.query)
        
        # Retrieve relevant documents
        search_results = await vector_service.search_documents(
            user_id=str(current_user.id),
            query_embedding=query_embedding,
            limit=rag_request.max_chunks,
            score_threshold=rag_request.score_threshold
        )
        
        # Format context documents
        context_documents = [
            {
                "chunk_id": result["id"],
                "document_id": result["document_id"],
                "score": result["score"],
                "text": result["text"],
                "source": result["source"],
                "page_number": result.get("page_number"),
                "chunk_index": result["chunk_index"],
                "doc_metadata": result["metadata"]
            }
            for result in search_results
        ]
        
        # Use user's LLM configuration if not specified
        llm_provider = rag_request.llm_provider or getattr(current_user, "llm_provider", None) or "anthropic"
        llm_model = rag_request.llm_model or getattr(current_user, "llm_model", None) or "claude-3-5-sonnet-20241022"
        
        # Generate streaming response
        response_stream = await llm_service.generate_rag_response(
            query=rag_request.query,
            context_documents=context_documents,
            provider=llm_provider,
            model=llm_model,
            system_prompt=rag_request.system_prompt,
            temperature=rag_request.temperature,
            max_tokens=rag_request.max_tokens,
            stream=True
        )
        
        # Create an initial query record (processing)
        query_record = Query(
            user_id=current_user.id,
            query_text=rag_request.query,
            query_type="rag",
            processing_time_ms=None,
            status="processing",
            retrieved_chunks_count=len(context_documents),
            retrieved_documents=[str(doc["document_id"]) for doc in context_documents],
            similarity_threshold=rag_request.score_threshold,
            llm_provider=llm_provider,
            llm_model=llm_model,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
            session_id=rag_request.session_id,
            conversation_turn=rag_request.conversation_turn,
            query_metadata={"rag_request": rag_request.model_dump(mode='json')}
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)

        buffered_content_parts: list[str] = []

        async def stream_generator():
            try:
                async for chunk in response_stream:
                    # buffer content to persist after stream ends
                    if isinstance(chunk, str):
                        buffered_content_parts.append(chunk)
                        yield f"data: {chunk}\n\n"
                    else:
                        # if provider yields dicts, try to extract 'content'
                        text = getattr(chunk, "content", None) or (chunk.get("content") if isinstance(chunk, dict) else None)
                        if text:
                            buffered_content_parts.append(text)
                            yield f"data: {text}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: [ERROR: {str(e)}]\n\n"
            finally:
                # Persist final response and mark query completed/failed (use a new DB session)
                try:
                    full_content = "".join(buffered_content_parts)
                    # Compute elapsed time from record creation to now
                    try:
                        processing_time = (time.time() - query_record.created_at.timestamp()) * 1000
                    except Exception:
                        processing_time = None
                    # Use a fresh session because request-scoped session may be closed
                    s = SessionLocal()
                    try:
                        q = s.query(Query).filter(Query.id == query_record.id).first()
                        if q:
                            q.processing_time_ms = processing_time
                            q.status = "completed" if full_content else "failed"
                            # Estimate token usage for streaming (approx 4 chars per token)
                            try:
                                context_text_concat = "\n\n".join([c["text"] for c in context_documents]) if context_documents else ""
                                prompt_text = (rag_request.query or "") + "\n\n" + context_text_concat
                                input_tokens_est = max(1, int(len(prompt_text) / 4)) if prompt_text else 0
                                output_tokens_est = max(1, int(len(full_content) / 4)) if full_content else 0
                                q.input_tokens = input_tokens_est
                                q.output_tokens = output_tokens_est
                                q.total_tokens = input_tokens_est + output_tokens_est
                                meta = dict(q.query_metadata or {})
                                meta["token_estimated"] = True
                                q.query_metadata = meta
                            except Exception:
                                pass
                            s.add(q)
                            s.commit()
                            if full_content and q.response is None:
                                response_record = QueryResponseModel(
                                    query_id=q.id,
                                    response_text=full_content,
                                    response_format="text",
                                    context_used="\n\n".join([c["text"] for c in context_documents]) if context_documents else "",
                                    context_chunks=[str(c["chunk_id"]) for c in context_documents],
                                    confidence_score=None,
                                    source_attribution=[c["source"] for c in context_documents],
                                    contains_citations=False,
                                    fact_checked=False
                                )
                                s.add(response_record)
                                s.commit()
                    finally:
                        s.close()
                except Exception as ex:
                    logger.error(f"Failed to persist streaming query: {ex}")

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming RAG query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Streaming RAG query failed"
        )


@router.get("/history", response_model=QueryHistory)
async def get_query_history(
    current_user: CurrentUserDep,
    db: DatabaseDep,
    skip: int = 0,
    limit: int = 20,
    session_id: Optional[str] = None
):
    """
    Get query history for the current user
    """
    try:
        query = db.query(Query).filter(
            Query.user_id == current_user.id
        )
        
        if session_id:
            query = query.filter(Query.session_id == session_id)
        
        query = query.order_by(Query.created_at.desc())
        
        total = query.count()
        queries = query.offset(skip).limit(limit).all()
        # Backfill any inconsistent records created by earlier streaming code
        repaired = False
        for q in queries:
            if getattr(q, "response", None) is not None and (q.status == "processing" or q.processing_time_ms is None):
                try:
                    # If we have a response, compute processing time if missing
                    if q.processing_time_ms is None and getattr(q.response, "generated_at", None):
                        q.processing_time_ms = (q.response.generated_at.timestamp() - q.created_at.timestamp()) * 1000
                    # Set status to completed if response exists
                    if q.status == "processing":
                        q.status = "completed"
                    db.add(q)
                    repaired = True
                except Exception:
                    pass
        if repaired:
            db.commit()
        
        return QueryHistory(
            queries=queries,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get query history"
        )


@router.get("/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: str,
    current_user: CurrentUserDep,
    db: DatabaseDep
):
    """
    Get specific query by ID
    """
    try:
        query = db.query(Query).filter(
            Query.id == query_id,
            Query.user_id == current_user.id
        ).first()
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        return query
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get query"
        )


@router.post("/{query_id}/feedback")
async def submit_query_feedback(
    query_id: str,
    feedback: QueryFeedback,
    current_user: CurrentUserDep,
    db: DatabaseDep
):
    """
    Submit feedback for a query
    """
    try:
        query = db.query(Query).filter(
            Query.id == query_id,
            Query.user_id == current_user.id
        ).first()
        
        if not query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        # Update query with feedback
        query.user_rating = feedback.rating
        query.feedback = feedback.feedback
        
        db.commit()
        
        logger.info(f"Feedback submitted for query {query_id} by {current_user.email}")
        return {"message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/analytics/summary", response_model=QueryAnalytics)
async def get_query_analytics(
    current_user: CurrentUserDep,
    db: DatabaseDep,
    days: int = 30
):
    """
    Get query analytics for the current user
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Base query for the period
        base_query = db.query(Query).filter(
            Query.user_id == current_user.id,
            Query.created_at >= start_date,
            Query.created_at <= end_date
        )
        
        # Total queries in period
        total_queries = base_query.count()
        
        # Queries today
        queries_today = db.query(Query).filter(
            Query.user_id == current_user.id,
            Query.created_at >= today_start
        ).count()
        
        # Average processing time
        avg_processing_time = base_query.filter(
            Query.processing_time_ms.isnot(None)
        ).with_entities(func.avg(Query.processing_time_ms)).scalar() or 0.0
        
        # Average tokens per query
        avg_tokens = base_query.filter(
            Query.total_tokens > 0
        ).with_entities(func.avg(Query.total_tokens)).scalar() or 0.0
        
        # Total cost
        total_cost = base_query.with_entities(
            func.sum(Query.estimated_cost)
        ).scalar() or 0.0
        
        # Top query types
        query_types = db.query(
            Query.query_type,
            func.count(Query.id).label('count')
        ).filter(
            Query.user_id == current_user.id,
            Query.created_at >= start_date
        ).group_by(Query.query_type).all()
        
        top_query_types = [
            {"type": qtype, "count": count} 
            for qtype, count in query_types
        ]
        
        # Average rating
        avg_rating = base_query.filter(
            Query.user_rating.isnot(None)
        ).with_entities(func.avg(Query.user_rating)).scalar()
        
        return QueryAnalytics(
            total_queries=total_queries,
            queries_today=queries_today,
            avg_processing_time_ms=float(avg_processing_time),
            avg_tokens_per_query=float(avg_tokens),
            total_cost=float(total_cost),
            top_query_types=top_query_types,
            avg_rating=float(avg_rating) if avg_rating else None,
            period_start=start_date,
            period_end=end_date
        )
        
    except Exception as e:
        logger.error(f"Failed to get query analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get query analytics"
        )