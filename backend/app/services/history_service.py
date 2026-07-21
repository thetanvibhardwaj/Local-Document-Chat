"""History service: read/manage chat sessions and their message history."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chat import ChatHistory, ChatSession
from app.schemas.chat import SessionCreateRequest


def create_session(db: Session, user_id: uuid.UUID, payload: SessionCreateRequest) -> ChatSession:
    session = ChatSession(user_id=user_id, session_name=payload.session_name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, user_id: uuid.UUID) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )


def get_session_history(db: Session, user_id: uuid.UUID, session_id: uuid.UUID | None = None) -> list[ChatHistory]:
    query = db.query(ChatHistory).filter(ChatHistory.user_id == user_id)
    if session_id is not None:
        query = query.filter(ChatHistory.session_id == session_id)
    return query.order_by(ChatHistory.timestamp.asc()).all()


def delete_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    db.delete(session)  # cascades to ChatHistory rows
    db.commit()
