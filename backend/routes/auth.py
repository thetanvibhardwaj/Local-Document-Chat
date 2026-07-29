import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database.connection import get_db
from backend.database.models import User, Document, ChatHistory
from backend.services.auth_service import AuthService
from backend.routes.schemas import (
    UserRegister, 
    UserResponse, 
    UserLogin, 
    TokenResponse, 
    UserProfileResponse, 
    MessageResponse
)
from backend.middleware.auth_middleware import get_current_user, get_token_from_header
from backend.utils.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post(
    "/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user in the SQLite database. Passwords are securely hashed using bcrypt."
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = AuthService.get_user_by_username(db, user_data.username)
    if existing_user:
        logger.warning(f"Registration failed: Username '{user_data.username}' is already taken.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered."
        )
    user = AuthService.create_user(db, user_data.username, user_data.password)
    return user

@router.post(
    "/login", 
    response_model=TokenResponse,
    summary="Log in and retrieve JWT token",
    description="Authenticates the user credentials. Upon success, returns a signed JWT token and registers a session."
)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = AuthService.authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password."
        )
    
    # Token expiration configuration
    access_token_expires = datetime.timedelta(minutes=60)
    token = AuthService.create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # Store token in active sessions database
    expires_at = datetime.datetime.utcnow() + access_token_expires
    AuthService.create_session(db, user.id, token, expires_at)
    
    logger.info(f"User '{user.username}' successfully logged in.")
    return {"access_token": token, "token_type": "bearer"}

@router.post(
    "/logout", 
    response_model=MessageResponse,
    summary="Log out and invalidate JWT token",
    description="Logs out the currently authenticated user by removing their active session token from the database."
)
def logout(
    token: str = Depends(get_token_from_header), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    success = AuthService.invalidate_session(db, token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session could not be logged out."
        )
    logger.info(f"User '{current_user.username}' successfully logged out.")
    return {"message": "Successfully logged out."}

@router.get(
    "/profile", 
    response_model=UserProfileResponse,
    summary="Get user profile statistics",
    description="Returns profile metrics of the authenticated user, including upload count, chat activity, and total file storage used."
)
def profile(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Retrieve counts and storage sums via SQLAlchemy query aggregation
    total_docs = db.query(Document).filter(Document.user_id == current_user.id).count()
    total_chats = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).count()
    
    storage_sum = db.query(func.sum(Document.size_bytes)).filter(Document.user_id == current_user.id).scalar()
    storage_used = storage_sum if storage_sum is not None else 0
    
    logger.info(f"Retrieved profile statistics for user '{current_user.username}'.")
    return {
        "username": current_user.username,
        "created_at": current_user.created_at,
        "total_documents": total_docs,
        "total_chats": total_chats,
        "storage_used_bytes": storage_used
    }
