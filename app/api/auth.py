"""
Authentication and user management API routes
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    UserSignup, UserSignupResponse
)
from app.dependencies import (
    get_db, get_auth_service,
    get_current_active_user, require_admin_role,
    CurrentUserDep, AdminUserDep, DatabaseDep,
    AuthServiceDep
)
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserSignupResponse)
async def user_signup(
    signup_data: UserSignup,
    db: DatabaseDep,
    auth_service: AuthServiceDep
):
    """
    Sign up for a new user account
    """
    try:
        # Create user
        user = auth_service.create_user(
            db=db,
            email=signup_data.email,
            username=signup_data.username,
            password=signup_data.password,
            role="user",
            llm_provider=signup_data.llm_provider or "openai",
            llm_model=signup_data.llm_model or "gpt-3.5-turbo"
        )
        
        # Generate access token for immediate login
        access_token = auth_service.create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            permissions=["read", "write"]
        )
        
        logger.info(f"User signup completed: {signup_data.email}")
        
        return UserSignupResponse(
            message="User created successfully",
            user=UserResponse.model_validate(user),
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User signup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed"
        )




@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    db: DatabaseDep,
    auth_service: AuthServiceDep
):
    """
    Authenticate user and return JWT token
    """
    try:
        # Authenticate user
        user = auth_service.authenticate_user(
            db=db,
            email=login_data.email,
            password=login_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Get user permissions (could be extended based on role)
        permissions = []
        if user.role == "admin":
            permissions = ["read", "write", "delete", "manage"]
        elif user.role == "user":
            permissions = ["read", "write"]
        else:
            permissions = ["read"]
        
        # Create access token
        access_token = auth_service.create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            permissions=permissions
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUserDep
):
    """
    Get current authenticated user information
    """
    return current_user














@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    current_user: CurrentUserDep,
    db: DatabaseDep,
    auth_service: AuthServiceDep
):
    """
    Refresh JWT token for current user
    """
    try:
        # Get user permissions
        permissions = []
        if current_user.role == "admin":
            permissions = ["read", "write", "delete", "manage"]
        elif current_user.role == "user":
            permissions = ["read", "write"]
        else:
            permissions = ["read"]
        
        # Create new access token
        access_token = auth_service.create_access_token(
            user_id=str(current_user.id),
            email=current_user.email,
            role=current_user.role,
            permissions=permissions
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
            user=UserResponse.model_validate(current_user)
        )
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )