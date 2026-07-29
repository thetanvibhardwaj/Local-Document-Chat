import os
import sys

# Safeguard: Resolve pathing issues if running directly from within the backend directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

# Safeguard: Prevent other packages from crashing on sys.stderr.flush() [Errno 22] in redirected console pipes
try:
    original_stderr_flush = sys.stderr.flush
    def safe_stderr_flush():
        try:
            original_stderr_flush()
        except OSError as e:
            if e.errno == 22:
                pass  # Ignore Errno 22 (Invalid argument)
            else:
                raise
    sys.stderr.flush = safe_stderr_flush
except Exception:
    pass

try:
    original_stdout_flush = sys.stdout.flush
    def safe_stdout_flush():
        try:
            original_stdout_flush()
        except OSError as e:
            if e.errno == 22:
                pass  # Ignore Errno 22 (Invalid argument)
            else:
                raise
    sys.stdout.flush = safe_stdout_flush
except Exception:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.connection import Base, engine
from backend.routes import auth_router, docs_router, chat_router
from backend.utils.config import settings
from backend.utils.logger import logger

# Auto-initialize database tables on app startup
try:
    logger.info("Performing startup database schema verification...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas validated successfully.")
except Exception as e:
    logger.critical(f"Database schema initialization failed: {e}", exc_info=True)
    raise e

app = FastAPI(
    title="Cognify Docs API",
    description=(
        "Production-inspired API layer for the AI-Powered Local Document Question "
        "Answering System (RAG). Includes JWT authorization, document upload pipelines, "
        "and contextual query generation using FAISS and Google Gemini."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable Cross-Origin Resource Sharing (CORS)
# Required for Streamlit or custom frontends running on other ports to interact with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production networks
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register sub-routes
app.include_router(auth_router)
app.include_router(docs_router)
app.include_router(chat_router)

@app.get("/", tags=["Health Check"])
def root():
    """Health check endpoint to verify backend operational status."""
    return {
        "status": "healthy",
        "application": "Cognify Docs API",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # Set app_dir to project root so that Uvicorn and its reload workers can always resolve the 'backend' package imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger.info(f"Launching Uvicorn server on {settings.host}:{settings.port}...")
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        app_dir=project_root
    )
