# API Reference

Base URL: `http://localhost:8000/api/v1`

All non-`/auth/*` endpoints require:
Authorization: Bearer <your-jwt-token>

Common error codes: 400, 401, 403, 404, 422, 500

## Authentication

POST /auth/signup
- Body: { email, username, password, llm_provider?, llm_model? }
- Response: { message, user, access_token, token_type, expires_in }

POST /auth/login
- Body: { email, password }
- Response: { access_token, token_type, expires_in, user }

GET /auth/me
- Response: User

POST /auth/refresh-token
- Response: { access_token, token_type, expires_in, user }

## Documents

POST /documents/upload
- Multipart form:
  - file: pdf | txt | docx
  - metadata: JSON string (optional)
- Response: DocumentResponse

GET /documents?skip=0&limit=100&status=
- Response: { documents: DocumentResponse[], total, page, size, pages }

GET /documents/{document_id}
- Response: DocumentResponse

DELETE /documents/{document_id}
- Response: { message }

POST /documents/{document_id}/process?force_reprocess=false
- Response: DocumentProcessResponse (processing | already_processed)

GET /documents/{document_id}/chunks?skip=0&limit=50
- Response: DocumentChunkResponse[]

POST /documents/search
- Body: { query: string, limit?: number, score_threshold?: number, document_ids?: string[] }
- Response: DocumentSearchResponse

## Queries & RAG

POST /queries/rag
- Body (RAGRequest):
  - query: string
  - max_chunks?: number (default 5)
  - score_threshold?: number (default 0.3)
  - temperature?: number (default 0.7)
  - max_tokens?: number (default 1000)
  - include_sources?: boolean (default true)
  - session_id?: string (recommended)
  - llm_provider?: string (defaults to user or `anthropic`)
  - llm_model?: string (defaults to user or `claude-3-5-sonnet-20241022`)
- Response (RAGResponse):
  - response, context_documents, context_used
  - processing_time_ms
  - llm_provider, llm_model
  - input_tokens, output_tokens, total_tokens (exact in non-stream)
  - estimated_cost
  - session_id, conversation_turn, created_at

POST /queries/rag/stream
- Body: same as above
- Response: text/plain lines:
  - data: <text>
  - ...
  - data: [DONE]
- Persistence:
  - Creates Query (status=processing) at start.
  - On finish: updates status to completed/failed, sets processing_time_ms, creates QueryResponse.
  - Token counts saved for streaming are currently estimated (see Notes).

GET /queries/history?skip=0&limit=20&session_id=
- Response: { queries: Query[], total, page, size, pages }
- Note: If a response exists but status was stuck in processing, this endpoint repairs the status and backfills processing_time_ms.

GET /queries/{query_id}
- Response: Query (with nested response)

POST /queries/{query_id}/feedback
- Body: { rating: 1..5, feedback?: string }
- Response: { message }

## Analytics

GET /queries/analytics/summary?days=30
- Response:
  {
    total_queries,
    queries_today,
    avg_processing_time_ms,
    avg_tokens_per_query,
    total_cost,
    top_query_types: [{ type, count }],
    avg_rating?,
    period_start,
    period_end
  }

## Debug

GET /queries/debug/vector-status
- Response: { collection_exists, total_vectors, user_documents, user_id, sample_documents }

GET /queries/debug/search-test?query=test&max_chunks=5&score_threshold=0.3
- Response: Debug search report with sample results/scores

## Key Schemas (summary)

Query
- id, user_id, query_text, query_type, processing_time_ms, status,
  retrieved_chunks_count, retrieved_documents[], similarity_threshold,
  llm_provider, llm_model, input_tokens, output_tokens, total_tokens,
  estimated_cost, user_rating?, feedback?, session_id?, conversation_turn,
  query_metadata, created_at, updated_at, response?

QueryResponse
- id, query_id, response_text, response_format, context_used, context_chunks[],
  confidence_score?, source_attribution[], contains_citations, fact_checked,
  is_cached, cache_hit, generated_at, created_at, updated_at

## Notes

- Token usage:
  - Non-streaming: exact counts saved from provider usage.
  - Streaming: estimated counts saved (approximation based on text length). Flagged with `query_metadata.token_estimated = true`.
- session_id is supported and recommended for chat continuity across reloads/navigation.