"""
Chat service: coordinates the RAG chain, session management, and
persistence of each question/answer pair into ChatHistory.
"""
import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chat import ChatHistory, ChatSession
from app.rag.chains import answer_question
from app.schemas.chat import ChatResponse, SourceReference
from app.utils import get_logger

logger = get_logger(__name__)


def _get_or_create_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID | None) -> ChatSession:
    if session_id is not None:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat session not found.")
        return session

    session = ChatSession(user_id=user_id, session_name="New Chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def ask_question(db: Session, user_id: uuid.UUID, question: str, session_id: uuid.UUID | None) -> ChatResponse:
    session = _get_or_create_session(db, user_id, session_id)

    result = answer_question(db=db, user_id=user_id, question=question)

    history_row = ChatHistory(
        user_id=user_id,
        session_id=session.id,
        question=question,
        answer=result.answer,
        source_documents=json.dumps(sorted({s.filename for s in result.sources})),
    )
    db.add(history_row)

    # Auto-name a fresh session after the first question, for a nicer sidebar UX.
    if session.session_name == "New Chat":
        session.session_name = question[:60] + ("..." if len(question) > 60 else "")

    db.commit()
    db.refresh(history_row)

    sources = [
        SourceReference(
            document_id=s.document_id,
            filename=s.filename,
            chunk_number=s.chunk_number,
            similarity_score=s.similarity_score,
        )
        for s in result.sources
    ]

    logger.info("Answered question for user %s in session %s (%d sources)", user_id, session.id, len(sources))

    return ChatResponse(
        session_id=session.id,
        question=question,
        answer=result.answer,
        sources=sources,
        timestamp=history_row.timestamp,
    )
