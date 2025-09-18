"""
Query-related database models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from app.database.base import Base


class Query(Base):
    """
    Query model for storing user queries and RAG context
    Tracks query history per user for analytics and improvement
    """
    __tablename__ = "queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Query Information
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), default="search")  # search, chat, summarize
    
    # Processing Information
    processing_time_ms = Column(Float, nullable=True)
    status = Column(String(50), default="completed", index=True)  # processing, completed, failed
    
    # Retrieval Context
    retrieved_chunks_count = Column(Integer, default=0)
    retrieved_documents = Column(JSON, default=list)  # List of document IDs used
    similarity_threshold = Column(Float, default=0.7)
    
    # LLM Information
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    prompt_template = Column(Text, nullable=True)
    
    # Token Usage (for cost tracking)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    
    # Quality Metrics
    user_rating = Column(Integer, nullable=True)  # 1-5 rating
    feedback = Column(Text, nullable=True)
    
    # Session Information
    session_id = Column(String(100), nullable=True, index=True)
    conversation_turn = Column(Integer, default=1)
    
    # Metadata
    query_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="queries")
    response = relationship("QueryResponse", back_populates="query", uselist=False)
    
    def __repr__(self):
        return f"<Query(id={self.id}, query_text='{self.query_text[:50]}...', user_id={self.user_id})>"


class QueryResponse(Base):
    """
    Query response model for storing generated responses
    Separated from Query for better data organization and caching
    """
    __tablename__ = "query_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id"), nullable=False, unique=True, index=True)
    
    # Response Content
    response_text = Column(Text, nullable=False)
    response_format = Column(String(50), default="text")  # text, markdown, html
    
    # Context Information
    context_used = Column(Text, nullable=True)  # The retrieved context used
    context_chunks = Column(JSON, default=list)  # List of chunk IDs used
    
    # Generation Metadata
    confidence_score = Column(Float, nullable=True)
    source_attribution = Column(JSON, default=list)  # Sources used in response
    
    # Quality Control
    contains_citations = Column(Boolean, default=False)
    fact_checked = Column(Boolean, default=False)
    
    # Cache Information
    is_cached = Column(Boolean, default=False)
    cache_hit = Column(Boolean, default=False)
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    query = relationship("Query", back_populates="response")
    
    def __repr__(self):
        return f"<QueryResponse(id={self.id}, query_id={self.query_id})>"