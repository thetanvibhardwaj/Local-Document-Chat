"""
Centralized application configuration.
All values are loaded from environment variables (.env in development,
real environment variables in production). Never hardcode secrets here.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "DocuChat AI"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/api/v1"

    # --- Security / JWT ---
    JWT_SECRET_KEY: str = Field(..., description="Secret key for signing JWTs")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)  # 24 hours

    # --- Database (Neon PostgreSQL) ---
    DATABASE_URL: str = Field(
        ..., description="postgresql+psycopg://user:pass@host/dbname?sslmode=require"
    )

    # --- Gemini ---
    GOOGLE_API_KEY: str = Field(..., description="Google Gemini API key")
    GEMINI_LLM_MODEL: str = Field(default="gemini-2.0-flash")
    GEMINI_EMBEDDING_MODEL: str = Field(default="models/text-embedding-004")
    EMBEDDING_DIMENSIONS: int = Field(default=768)

    # --- RAG / Chunking ---
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=200)
    RETRIEVAL_TOP_K: int = Field(default=5)
    SIMILARITY_SCORE_THRESHOLD: float = Field(default=0.3)

    # --- Uploads ---
    UPLOAD_DIR: str = Field(default="uploads")
    MAX_UPLOAD_SIZE_MB: int = Field(default=25)
    ALLOWED_EXTENSIONS: List[str] = Field(default=["pdf", "docx", "txt", "md"])

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:8501"])

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # --- Logging ---
    LOG_LEVEL: str = Field(default="INFO")
    LOG_DIR: str = Field(default="logs")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so .env is parsed only once."""
    return Settings()


settings = get_settings()
