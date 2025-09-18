"""
Authentication-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


# User schemas
class UserCreate(BaseModel):
    """Schema for creating new user"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: str = Field(default="user")


class UserSignup(BaseModel):
    """Schema for user signup"""
    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password")
    
    # Optional Configuration
    llm_provider: Optional[str] = Field(default="openai", description="LLM provider")
    llm_model: Optional[str] = Field(default="gpt-3.5-turbo", description="LLM model")


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: str
    username: str
    role: str
    llm_provider: str
    llm_model: str
    is_active: bool
    email_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserSignupResponse(BaseModel):
    """Schema for user signup response"""
    message: str
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int

