"""
Authentication service for per-user JWT authentication
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from app.models.user import User
from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Authentication service handling JWT tokens and per-user management
    """
    
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.jwt_expire_minutes
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str,
        permissions: Optional[list] = None
    ) -> str:
        """
        Create JWT access token for user
        """
        if permissions is None:
            permissions = []
            
        # Token payload with user context
        payload = {
            "user_id": str(user_id),
            "email": email,
            "role": role,
            "permissions": permissions,
            "exp": datetime.utcnow() + timedelta(minutes=self.expire_minutes),
            "iat": datetime.utcnow(),
            "iss": settings.app_name,
            "type": "access_token"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token
        Returns token payload if valid
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != "access_token":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def authenticate_user(
        self, 
        db: Session, 
        email: str, 
        password: str
    ) -> Optional[User]:
        """
        Authenticate user with email/password
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
            
        if not self.verify_password(password, user.hashed_password):
            return None
            
        if not user.is_active:
            return None
            
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    def create_user(
        self,
        db: Session,
        email: str,
        username: str,
        password: str,
        role: str = "user",
        llm_provider: str = "openai",
        llm_model: str = "gpt-3.5-turbo"
    ) -> User:
        """
        Create new user
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        
        # Create new user
        hashed_password = self.hash_password(password)
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=role,
            llm_provider=llm_provider,
            llm_model=llm_model,
            is_active=True,
            email_verified=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    def get_user_by_token(self, db: Session, token: str) -> User:
        """
        Get user from JWT token
        """
        payload = self.decode_token(token)
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Prefer querying by email (unique and DB-agnostic)
        user = None
        if email:
            user = db.query(User).filter(
                and_(
                    User.email == email,
                    User.is_active == True
                )
            ).first()
        
        if not user and user_id:
            # Fallback: normalize UUID string from token to UUID object when supported by the DB/dialect
            try:
                user_uuid = uuid.UUID(str(user_id))
            except Exception:
                user_uuid = user_id  # fallback to raw value if not a valid UUID string
            user = db.query(User).filter(
                and_(
                    User.id == user_uuid,
                    User.is_active == True
                )
            ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
    
    def get_user_id_from_token(self, token: str) -> str:
        """
        Extract user ID from JWT token
        """
        payload = self.decode_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Return standardized string UUID
        try:
            return str(uuid.UUID(str(user_id)))
        except Exception:
            return str(user_id)
    
    def check_permission(
        self, 
        token: str, 
        required_permission: str
    ) -> bool:
        """
        Check if user has specific permission
        """
        payload = self.decode_token(token)
        permissions = payload.get("permissions", [])
        role = payload.get("role", "user")
        
        # Admin role has all permissions
        if role == "admin":
            return True
        
        return required_permission in permissions