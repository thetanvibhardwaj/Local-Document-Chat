from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User, ChatHistory, Document
from backend.services.rag_service import RAGService
from backend.routes.schemas import ChatRequest, ChatResponse, ChatHistoryResponse
from backend.middleware.auth_middleware import get_current_user
from backend.utils.logger import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.post(
    "", 
    response_model=ChatResponse,
    summary="Ask a question about uploaded documents",
    description="Uses RAG pipeline to search document context and generate an answer with citations. Logs to chat history."
)
def chat_query(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User '{current_user.username}' submitted query: '{request.question}'")
    
    # 1. If filtering by a document, verify that it exists and belongs to this user
    if request.document_id is not None:
        doc = db.query(Document).filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id
        ).first()
        if not doc:
            logger.warning(f"Chat failed: Document {request.document_id} not found or unauthorized for user '{current_user.username}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document filter targets a non-existent or inaccessible document."
            )
            
    # 2. Run the RAG search and model generation
    rag_result = RAGService.query_rag(
        user_id=current_user.id,
        question=request.question,
        document_id=request.document_id
    )
    
    # 3. Log interaction to ChatHistory table in database
    try:
        chat_log = ChatHistory(
            question=request.question,
            answer=rag_result["answer"],
            user_id=current_user.id,
            document_id=request.document_id
        )
        db.add(chat_log)
        db.commit()
        logger.info(f"Logged conversation to SQLite history (User ID: {current_user.id}).")
    except Exception as e:
        logger.error(f"Failed to log chat interaction to DB: {e}", exc_info=True)
        # We don't raise an exception to prevent breaking the response delivery to the user
        
    return rag_result

@router.get(
    "/history", 
    response_model=List[ChatHistoryResponse],
    summary="Retrieve chat history",
    description="Fetches previous QA history. Supports searching text keywords and filtering by specific document ID."
)
def get_chat_history(
    q: Optional[str] = Query(None, description="Search keyword in questions or answers"),
    document_id: Optional[int] = Query(None, description="Filter history logs by specific document ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User '{current_user.username}' requested chat history (Query: '{q}', Doc Filter: {document_id}).")
    
    query = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id)
    
    # Apply keyword text filter if supplied
    if q and q.strip() != "":
        search_filter = f"%{q.strip()}%"
        query = query.filter(
            (ChatHistory.question.ilike(search_filter)) | 
            (ChatHistory.answer.ilike(search_filter))
        )
        
    # Apply document ID filter if supplied
    if document_id is not None:
        query = query.filter(ChatHistory.document_id == document_id)
        
    # Retrieve ordered by latest timestamps
    db_history = query.order_by(ChatHistory.timestamp.desc()).all()
    
    # Map model instances to responses with lazy document name resolves
    history_response = []
    for item in db_history:
        history_response.append({
            "id": item.id,
            "question": item.question,
            "answer": item.answer,
            "timestamp": item.timestamp,
            "document_id": item.document_id,
            "document_name": item.document.filename if item.document else None
        })
        
    return history_response
