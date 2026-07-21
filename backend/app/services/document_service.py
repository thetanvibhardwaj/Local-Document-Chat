"""
Document service: orchestrates the full upload -> index pipeline
(save file -> extract -> clean -> chunk -> embed -> store -> metadata).
"""
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.rag.chunking import split_text
from app.rag.embeddings import embed_documents
from app.rag.loaders import UnsupportedFileTypeError, load_document
from app.utils import clean_text, get_logger, validate_upload

logger = get_logger(__name__)


def _save_file_to_disk(file: UploadFile, user_id: uuid.UUID, extension: str) -> Path:
    user_dir = Path(settings.UPLOAD_DIR) / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4()}.{extension}"
    destination = user_dir / unique_name

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return destination


def upload_and_index_document(db: Session, user_id: uuid.UUID, file: UploadFile) -> Document:
    """
    Full pipeline: validate -> save -> extract -> clean -> chunk -> embed -> persist.
    Rolls back the document record and deletes the saved file if any step fails,
    so partial/broken documents never linger in a "ready" or ambiguous state.
    """
    extension = validate_upload(file)
    stored_path = _save_file_to_disk(file, user_id, extension)
    file_size = stored_path.stat().st_size

    document = Document(
        user_id=user_id,
        filename=file.filename,
        stored_path=str(stored_path),
        file_type=extension,
        file_size_bytes=file_size,
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        raw_text = load_document(str(stored_path), extension)
        cleaned = clean_text(raw_text)

        if not cleaned:
            raise ValueError("No extractable text found in document.")

        chunks = split_text(cleaned)
        if not chunks:
            raise ValueError("Document produced zero chunks after splitting.")

        embeddings = embed_documents(chunks)

        chunk_rows = [
            DocumentChunk(
                document_id=document.id,
                chunk_text=chunk_text,
                chunk_number=idx,
                embedding=embedding,
            )
            for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings))
        ]
        db.add_all(chunk_rows)

        document.total_chunks = len(chunk_rows)
        document.status = "ready"
        db.commit()
        db.refresh(document)

        logger.info("Indexed document %s (%d chunks) for user %s", document.filename, len(chunk_rows), user_id)
        return document

    except (UnsupportedFileTypeError, ValueError, FileNotFoundError) as exc:
        document.status = "failed"
        db.commit()
        logger.error("Failed to index document %s: %s", document.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process document: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001 - convert any pipeline failure into a clean 500
        document.status = "failed"
        db.commit()
        logger.exception("Unexpected error indexing document %s", document.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the document.",
        ) from exc


def list_user_documents(db: Session, user_id: uuid.UUID) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.upload_time.desc())
        .all()
    )


def delete_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

    stored_path = Path(document.stored_path)
    if stored_path.exists():
        stored_path.unlink(missing_ok=True)

    db.delete(document)  # cascades to DocumentChunk rows
    db.commit()
    logger.info("Deleted document %s for user %s", document_id, user_id)


def reindex_document(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    """Re-run extraction/chunking/embedding for an already-uploaded file."""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    document.status = "processing"
    db.commit()

    raw_text = load_document(document.stored_path, document.file_type)
    cleaned = clean_text(raw_text)
    chunks = split_text(cleaned)
    embeddings = embed_documents(chunks)

    chunk_rows = [
        DocumentChunk(document_id=document.id, chunk_text=t, chunk_number=i, embedding=e)
        for i, (t, e) in enumerate(zip(chunks, embeddings))
    ]
    db.add_all(chunk_rows)
    document.total_chunks = len(chunk_rows)
    document.status = "ready"
    db.commit()
    db.refresh(document)
    return document
