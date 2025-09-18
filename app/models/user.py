"""
User-related database models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.base import Base


class User(Base):
    """
    User model for simple per-user authentication
    Each user has their own isolated documents and queries
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User Information
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # User Preferences 
    llm_provider = Column(String(50), default="openai")
    llm_model = Column(String(100), default="gpt-3.5-turbo")
    embedding_model = Column(String(100), default="sentence-transformers/all-MiniLM-L6-v2")
    
    # Role and Permissions
    role = Column(String(50), default="user")  # admin, user, viewer
    permissions = Column(Text)  # JSON string of permissions
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    email_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
