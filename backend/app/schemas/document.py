"""Pydantic schemas for document management endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int
    total_chunks: int
    status: str
    upload_time: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str = "Document uploaded and indexed successfully."


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
