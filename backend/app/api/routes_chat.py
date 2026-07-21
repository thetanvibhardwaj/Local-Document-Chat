"""Chat, chat-history, and session management routes."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    SessionCreateRequest,
    SessionResponse,
)
from app.services import chat_service, history_service

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    return chat_service.ask_question(db, current_user.id, payload.question, payload.session_id)


@router.get("/chat/history", response_model=list[ChatHistoryItem])
def get_history(
    session_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatHistoryItem]:
    rows = history_service.get_session_history(db, current_user.id, session_id)
    return [ChatHistoryItem.model_validate(r) for r in rows]


@router.get("/chat/sessions", response_model=list[SessionResponse])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionResponse]:
    sessions = history_service.list_sessions(db, current_user.id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.post("/chat/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    session = history_service.create_session(db, current_user.id, payload)
    return SessionResponse.model_validate(session)


@router.delete("/chat/session/{session_id}", status_code=204)
def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    history_service.delete_session(db, current_user.id, session_id)
