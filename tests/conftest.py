"""
Shared pytest fixtures.
Uses a TestClient against the real FastAPI app. For true isolation, point
DATABASE_URL (via .env.test or CI secrets) at a disposable Neon branch or
a local pgvector-enabled Postgres instance before running these tests.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def test_user_payload() -> dict:
    return {
        "username": "test_user_pytest",
        "email": "test_user_pytest@example.com",
        "password": "TestPass123",
    }
