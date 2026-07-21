"""
Gemini embeddings wrapper.
Wraps LangChain's GoogleGenerativeAIEmbeddings so the rest of the app never
touches the Gemini SDK directly -- this keeps provider swaps (e.g. to a
different embedding model) contained to one file.
"""
from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import settings


@lru_cache
def get_embeddings_client() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.GEMINI_EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of chunk texts (used during document indexing)."""
    client = get_embeddings_client()
    return client.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    """Embed a single user question (used during retrieval)."""
    client = get_embeddings_client()
    return client.embed_query(text)
