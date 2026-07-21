"""Pydantic schemas for chat endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: uuid.UUID | None = None


class SourceReference(BaseModel):
    document_id: uuid.UUID
    filename: str
    chunk_number: int
    similarity_score: float


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    question: str
    answer: str
    sources: list[SourceReference]
    timestamp: datetime


class ChatHistoryItem(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    question: str
    answer: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: uuid.UUID
    session_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionCreateRequest(BaseModel):
    session_name: str = Field(default="New Chat", max_length=255)
