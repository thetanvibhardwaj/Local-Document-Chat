import os
from pathlib import Path
import sys

# Safeguard: Globally disable tqdm progress bars to prevent sys.stderr.flush() [Errno 22] in redirected console streams
try:
    import tqdm
    original_tqdm_init = tqdm.tqdm.__init__
    def safe_tqdm_init(self, *args, **kwargs):
        kwargs["disable"] = True
        original_tqdm_init(self, *args, **kwargs)
    tqdm.tqdm.__init__ = safe_tqdm_init
except Exception:
    pass

# Safeguard: Disable transformers logging progress bars
try:
    from transformers.utils.logging import disable_progress_bar
    disable_progress_bar()
except Exception:
    pass

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (cognify_docs/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    host: str = Field(default="127.0.0.1", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    database_url: str = Field(
        default="sqlite:///./backend/database/cognify_docs.db",
        validation_alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="", validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    upload_dir: str = Field(default="./uploads", validation_alias="UPLOAD_DIR")
    vector_store_dir: str = Field(default="./vector_store", validation_alias="VECTOR_STORE_DIR")
    log_file_path: str = Field(default="./logs/app.log", validation_alias="LOG_FILE_PATH")
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL_NAME",
    )
    max_upload_size_mb: int = Field(
        default=10,
        validation_alias="MAX_UPLOAD_SIZE_MB",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# -----------------------------
# Absolute Paths
# -----------------------------

# Database
db_path = PROJECT_ROOT / "backend" / "database" / "cognify_docs.db"
db_path.parent.mkdir(parents=True, exist_ok=True)
settings.database_url = f"sqlite:///{db_path.as_posix()}"

# Uploads
upload_path = PROJECT_ROOT / "uploads"
upload_path.mkdir(parents=True, exist_ok=True)
settings.upload_dir = str(upload_path)

# Vector Store
vector_store_path = PROJECT_ROOT / "vector_store"
vector_store_path.mkdir(parents=True, exist_ok=True)
settings.vector_store_dir = str(vector_store_path)

# Logs
logs_path = PROJECT_ROOT / "logs"
logs_path.mkdir(parents=True, exist_ok=True)
settings.log_file_path = str(logs_path / "app.log")

# -----------------------------
# Debug Prints
# -----------------------------
print("=" * 60)
print("PROJECT ROOT :", PROJECT_ROOT)
print("WORKING DIR  :", os.getcwd())
print("ENV FILE     :", PROJECT_ROOT / ".env")
print("Gemini Key   :", settings.gemini_api_key)
print("Database URL :", settings.database_url)
print("Upload Dir   :", settings.upload_dir)
print("Vector Store :", settings.vector_store_dir)
print("Log File     :", settings.log_file_path)
print("=" * 60)