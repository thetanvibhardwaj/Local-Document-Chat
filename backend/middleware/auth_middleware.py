from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User
from backend.services.auth_service import AuthService
from backend.utils.config import settings
from backend.utils.logger import logger

# Declare OAuth2 Bearer security scheme
security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to extract and validate the JWT Bearer token from the
    Authorization header. It checks expiration and verifies the session in SQLite.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        logger.warning("Request missing Authorization credentials.")
        raise credentials_exception
        
    token = credentials.credentials
    
    # 1. Verify token exists in active sessions table (stateful invalidation)
    if not AuthService.is_session_valid(db, token):
        logger.warning("Rejected request: Session is inactive, expired, or logged out.")
        raise credentials_exception

    # 2. Decode and verify JWT signature/claims
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise credentials_exception
        
    # 3. Retrieve user entity from database
    user = AuthService.get_user_by_username(db, username)
    if user is None:
        logger.warning(f"User '{username}' referenced in token was not found in database.")
        raise credentials_exception
        
    return user

def get_token_from_header(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Simple dependency helper to extract the raw token string from HTTP header.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token."
        )
    return credentials.credentials
