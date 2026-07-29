import datetime
from typing import Optional
import bcrypt
from jose import jwt
from sqlalchemy.orm import Session
from backend.database.models import User, Session as UserSession
from backend.utils.config import settings
from backend.utils.logger import logger

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt directly."""
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hashed value using bcrypt directly."""
        try:
            pwd_bytes = plain_password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(pwd_bytes, hashed_bytes)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
        """Generate a signed JWT token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.datetime.utcnow() + expires_delta
        else:
            expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Fetch a user from the database by their username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create_user(db: Session, username: str, password: str) -> User:
        """Create a new user with a hashed password in the database."""
        hashed_password = AuthService.hash_password(password)
        db_user = User(username=username, hashed_password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User '{username}' registered successfully.")
        return db_user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Verify username and password against database records."""
        user = AuthService.get_user_by_username(db, username)
        if not user:
            logger.warning(f"Failed authentication attempt for non-existent user: {username}")
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            logger.warning(f"Failed authentication attempt (invalid password) for user: {username}")
            return None
        return user

    @staticmethod
    def create_session(db: Session, user_id: int, token: str, expires_at: datetime.datetime) -> UserSession:
        """Store an active session token in the database."""
        # Clean up expired sessions first to maintain database hygiene
        db.query(UserSession).filter(UserSession.expires_at < datetime.datetime.utcnow()).delete()
        
        db_session = UserSession(token=token, user_id=user_id, expires_at=expires_at)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session

    @staticmethod
    def invalidate_session(db: Session, token: str) -> bool:
        """Remove a session token from the database, effectively logging out the user."""
        db_session = db.query(UserSession).filter(UserSession.token == token).first()
        if db_session:
            db.delete(db_session)
            db.commit()
            logger.info(f"Session token invalidated successfully.")
            return True
        return False

    @staticmethod
    def is_session_valid(db: Session, token: str) -> bool:
        """Check if the session token is registered and active in the database."""
        db_session = db.query(UserSession).filter(
            UserSession.token == token,
            UserSession.expires_at > datetime.datetime.utcnow()
        ).first()
        return db_session is not None
