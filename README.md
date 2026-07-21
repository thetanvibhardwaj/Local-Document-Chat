# 📄 DocuChat AI

An enterprise-grade **AI-Powered Document Chat System** built with **Retrieval-Augmented Generation (RAG)**. Upload HR policies, manuals, technical docs, contracts, or reports — then ask questions in plain English and get answers grounded **strictly** in your own documents. No hallucination. No fabricated answers.

If the answer isn't in your documents, DocuChat AI says so:

> "I couldn't find relevant information in the uploaded documents."

---

## ✨ Features

- 🔐 JWT authentication with hashed passwords (bcrypt) and role-based access
- 📤 Drag-and-drop upload for PDF, DOCX, TXT, and Markdown
- 🧠 RAG pipeline: LangChain + Gemini Embeddings + Gemini LLM + pgvector
- 🔍 Cosine-similarity vector search scoped per user
- 💬 Multi-session chat with full history and source-document references
- 🎨 Streamlit UI with a dark/light luxury black & grey theme, drag-and-drop, and a typing animation
- 🧱 Clean, modular FastAPI backend, fully decoupled from the frontend (swap in React later with zero backend changes)
- 🐳 Docker & docker-compose ready
- ✅ Pytest-based test suite

---

## 🏗️ Architecture

```
Loader → Text Cleaning → Chunking (Recursive, 1000/200) → Gemini Embeddings
    → pgvector Storage → Retriever (cosine similarity) → Prompt Template
    → Gemini LLM → Output Parser → Answer + Sources
```

```
backend/
  app/
    api/            FastAPI routers (auth, documents, chat)
    auth/            JWT + password hashing + current-user dependency
    config/          Pydantic settings (env-driven)
    database/        SQLAlchemy engine/session/base
    models/          ORM models (User, Document, DocumentChunk, ChatSession, ChatHistory)
    schemas/         Pydantic request/response models
    services/        Business logic (document, chat, history services)
    rag/
      loaders/       PDF/DOCX/TXT/MD extraction
      chunking/      RecursiveCharacterTextSplitter wrapper
      embeddings/    Gemini embeddings client
      retriever/     pgvector cosine-similarity search
      prompts/       Strict, grounded-answer prompt templates
      chains/        End-to-end retrieve → prompt → LLM chain
    utils/           Logging, file validation, text cleaning
    main.py          FastAPI app, CORS, rate limiting, routers
  alembic/           Migrations (initial schema included)
frontend/
  streamlit_app.py   Pure REST client — no business logic
uploads/             User-uploaded files (gitignored contents)
logs/                Rotating app logs (gitignored contents)
tests/               Pytest suite
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.11+
- A [Neon](https://neon.tech) Postgres project (free tier is fine) with the `pgvector` extension available
- A [Google AI Studio](https://aistudio.google.com/) API key for Gemini

### 2. Clone & configure

```bash
cd docuchat-ai
cp .env.example .env
```

Edit `.env` and fill in:

- `JWT_SECRET_KEY` — generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- `DATABASE_URL` — from your Neon dashboard, e.g.
  `postgresql+psycopg://user:pass@ep-xxxx.neon.tech/docuchat?sslmode=require`
- `GOOGLE_API_KEY` — your Gemini API key

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run database migrations

Alembic reads `DATABASE_URL` straight from your `.env` (via `app.config.settings`), and the initial migration automatically runs `CREATE EXTENSION IF NOT EXISTS vector` before creating tables.

```bash
cd backend
alembic upgrade head
```

### 5. Run the backend

```bash
# from backend/
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### 6. Run the frontend

```bash
# from project root, in a second terminal
cd frontend
export BACKEND_API_URL=http://localhost:8000/api/v1   # Windows: set BACKEND_API_URL=...
streamlit run streamlit_app.py
```

Open `http://localhost:8501`, register an account, upload a document, and start chatting.

---

## 🐳 Docker

```bash
docker-compose up --build
```

- Backend → `http://localhost:8000`
- Frontend → `http://localhost:8501`

Docker Compose does **not** define a local Postgres container — this project targets Neon's managed serverless Postgres. If you'd rather run Postgres locally, add a `db` service using the `pgvector/pgvector:pg16` image and point `DATABASE_URL` at it.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/register` | Create a new user account |
| POST | `/api/v1/login` | Authenticate and receive a JWT |
| POST | `/api/v1/documents/upload` | Upload + index a document |
| GET | `/api/v1/documents` | List the current user's documents |
| DELETE | `/api/v1/documents/{id}` | Delete a document (and its chunks) |
| POST | `/api/v1/documents/{id}/reindex` | Re-run extraction/chunking/embedding |
| POST | `/api/v1/chat` | Ask a question (RAG pipeline) |
| GET | `/api/v1/chat/history` | Retrieve chat history (optionally by session) |
| GET | `/api/v1/chat/sessions` | List chat sessions |
| POST | `/api/v1/chat/sessions` | Create a new chat session |
| DELETE | `/api/v1/chat/session/{id}` | Delete a session (and its history) |

---

## 🧪 Testing

```bash
pytest tests/ -v
```

Tests exercise auth, document validation, and the RAG fallback behavior (no documents → strict "no information found" response) via FastAPI's `TestClient`. For full end-to-end coverage including real embeddings, point the test `.env` at a disposable Neon branch and a valid Gemini key.

---

## 🔒 Security Notes

- Passwords hashed with bcrypt (never stored in plaintext)
- JWT tokens with configurable expiry
- File extension whitelist + max upload size enforcement
- Rate limiting via `slowapi`
- All secrets loaded from environment variables — nothing hardcoded
- CORS explicitly configured per environment
- Documents and chat history are strictly scoped per user (no cross-user data leakage)

---

## 🗺️ Roadmap

- React frontend (backend API is already designed for this — no changes needed)
- Redis caching for repeated queries
- Hybrid (keyword + vector) search
- OCR for scanned PDFs and image understanding
- Voice chat
- Document summarization and an admin analytics dashboard
- Multi-tenant support, Kubernetes deployment, CI/CD pipeline

---

## ⚠️ Known Limitations (v1)

- `unstructured[md]` and some loaders may require additional system packages (e.g. `libmagic`) on certain Linux distros — install via your package manager if you hit extraction errors.
- The IVFFlat index built in the initial migration performs best once you have a non-trivial number of chunks; for very small datasets, a plain sequential scan is comparably fast.
- Streaming token-by-token responses from Gemini are not yet wired through the API (the Streamlit "typing animation" is a client-side effect on the completed answer) — true server-sent streaming is a natural next step once you're ready to move past Streamlit.
