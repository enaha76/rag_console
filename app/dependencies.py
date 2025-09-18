"""
FastAPI dependencies for authentication and service injection (per-user model)
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.vector_service import QdrantVectorService
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.cache_service import CacheService

# Security scheme for JWT authentication
security = HTTPBearer(auto_error=False)


# Service dependencies (singletons)
def get_auth_service() -> AuthService:
    """Get authentication service instance"""
    return AuthService()


def get_document_service() -> DocumentService:
    """Get document service instance"""
    return DocumentService()


def get_vector_service() -> QdrantVectorService:
    """Get vector service instance"""
    return QdrantVectorService()


def get_llm_service() -> LLMService:
    """Get LLM service instance"""
    return LLMService()


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    return EmbeddingService()


def get_cache_service() -> CacheService:
    """Get cache service instance"""
    return CacheService()


# Authentication dependencies
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = auth_service.get_user_by_token(db, credentials.credentials)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional validation)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


# Role-based access dependencies
def require_admin_role(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require admin role for endpoint access
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def require_user_or_admin_role(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user or admin role for endpoint access
    """
    if current_user.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User or admin role required"
        )
    return current_user


# Common type annotations for dependency injection
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
VectorServiceDep = Annotated[QdrantVectorService, Depends(get_vector_service)]
LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]

CurrentUserDep = Annotated[User, Depends(get_current_active_user)]
AdminUserDep = Annotated[User, Depends(require_admin_role)]
DatabaseDep = Annotated[Session, Depends(get_db)]