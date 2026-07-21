"""
Chunking strategy: RecursiveCharacterTextSplitter with chunk_size=1000
and chunk_overlap=200, per the project's RAG design.
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import settings


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_text(text: str) -> list[str]:
    """Split cleaned document text into overlapping chunks."""
    splitter = get_text_splitter()
    chunks = splitter.split_text(text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
