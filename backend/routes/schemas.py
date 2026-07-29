from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Authentication Schemas ---

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, description="Cleartext password")

class UserLogin(BaseModel):
    username: str = Field(...)
    password: str = Field(...)

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- Document Schemas ---

class DocumentResponse(BaseModel):
    id: int
    filename: str
    filepath: str
    file_type: str
    size_bytes: int
    chunk_count: int
    upload_date: datetime
    embedding_status: str

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    message: str

# --- Chat & RAG Schemas ---

class ChatRequest(BaseModel):
    question: str = Field(..., description="The query to ask the AI RAG system")
    document_id: Optional[int] = Field(None, description="ID of document to filter by. If null, search all documents.")

class Citation(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    chunk_text: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]

class ChatHistoryResponse(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: datetime
    document_id: Optional[int] = None
    document_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Profile Schemas ---

class UserProfileResponse(BaseModel):
    username: str
    created_at: datetime
    total_documents: int
    total_chats: int
    storage_used_bytes: int

    class Config:
        from_attributes = True
