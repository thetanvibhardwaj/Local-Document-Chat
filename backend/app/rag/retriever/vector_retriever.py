"""
pgvector-backed similarity search.
Retrieves the top-K most similar chunks for a given user question, scoped
to a specific user (and optionally a specific document) so users never see
each other's documents.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.rag.embeddings import embed_query


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    chunk_number: int
    chunk_text: str
    similarity_score: float


def retrieve_relevant_chunks(
    db: Session,
    user_id: uuid.UUID,
    question: str,
    top_k: int | None = None,
    document_id: uuid.UUID | None = None,
) -> list[RetrievedChunk]:
    """
    Embed the question and run a cosine-distance nearest-neighbor search
    against pgvector, scoped to the requesting user's documents only.
    """
    top_k = top_k or settings.RETRIEVAL_TOP_K
    query_embedding = embed_query(question)

    # cosine_distance: 0 = identical, 2 = opposite. Similarity = 1 - distance.
    distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(DocumentChunk, Document.filename, distance_expr.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == user_id, Document.status == "ready")
        .order_by(distance_expr)
        .limit(top_k)
    )

    if document_id is not None:
        stmt = stmt.where(Document.id == document_id)

    results = db.execute(stmt).all()

    retrieved: list[RetrievedChunk] = []
    for chunk, filename, distance in results:
        similarity = 1 - float(distance)
        if similarity < settings.SIMILARITY_SCORE_THRESHOLD:
            continue
        retrieved.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                chunk_number=chunk.chunk_number,
                chunk_text=chunk.chunk_text,
                similarity_score=round(similarity, 4),
            )
        )
    return retrieved
