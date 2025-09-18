"""
Document-related database models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database.base import Base


class Document(Base):
    """
    Document model for storing uploaded documents metadata
    Each document belongs to a specific user for isolation
    """
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Document Information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # Processing Status
    status = Column(String(50), default="uploaded", index=True)  # uploaded, processing, processed, failed
    total_chunks = Column(Integer, default=0)
    processed_chunks = Column(Integer, default=0)
    
    # Content Metadata
    title = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    language = Column(String(10), default="en")
    word_count = Column(Integer, default=0)
    
    # Vector Store Information
    collection_name = Column(String(100), nullable=True)
    embedding_model = Column(String(100), nullable=True)
    
    # Additional Metadata
    doc_metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', user_id={self.user_id})>"


class DocumentChunk(Base):
    """
    Document chunk model for storing text chunks with embeddings
    Used for efficient retrieval in RAG pipeline
    """
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Chunk Information
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    
    # Position in Document
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=True)
    
    # Vector Information
    vector_id = Column(String(100), nullable=True, index=True)  # ID in Qdrant
    embedding_model = Column(String(100), nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    
    # Similarity Scores (for caching)
    last_similarity_score = Column(Float, nullable=True)
    
    # Metadata
    doc_metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    user = relationship("User")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, chunk_index={self.chunk_index}, document_id={self.document_id})>"