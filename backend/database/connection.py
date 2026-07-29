from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.utils.config import settings
from backend.utils.logger import logger

# SQLite specific argument: check_same_thread=False
# This allows multi-threaded FastAPI handlers to share SQLite connection contexts safely
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False  # Set to True for verbose SQL logging
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Database engine initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing database engine: {e}")
    raise e

def get_db():
    """
    FastAPI dependency that yields a database session and ensures
    it gets closed after the request lifecycle completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
