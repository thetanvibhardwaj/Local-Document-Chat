import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database.connection import Base, get_db

# Isolated SQLite file specifically for automated testing
TEST_DB_PATH = "./backend/database/test_cognify.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

@pytest.fixture(scope="module")
def test_db():
    """
    Creates an isolated database, initializes all schema tables,
    yields a sessionmaker, and cleans up the SQLite file afterwards.
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

@pytest.fixture(scope="module")
def client(test_db):
    """
    FastAPI TestClient fixture that overrides get_db dependency
    to use the isolated testing database.
    """
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()
