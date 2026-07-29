from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User
from backend.services.doc_service import DocumentService
from backend.routes.schemas import DocumentResponse, MessageResponse
from backend.middleware.auth_middleware import get_current_user
from backend.utils.logger import logger

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.post(
    "/upload", 
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document (PDF, DOCX, TXT)",
    description="Uploads a local file. The backend parses it, stores context chunks in SQLite, and creates FAISS embeddings."
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User '{current_user.username}' initiated upload of file '{file.filename}'.")
    # Delegate parsing and vector generation to DocumentService
    return DocumentService.upload_and_process_document(db, file, current_user.id)

@router.get(
    "", 
    response_model=List[DocumentResponse],
    summary="List all user documents",
    description="Retrieves a list of all documents uploaded by the currently authenticated user."
)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User '{current_user.username}' requested document list.")
    return DocumentService.get_user_documents(db, current_user.id)

@router.get(
    "/{id}", 
    response_model=DocumentResponse,
    summary="Get document details",
    description="Retrieves the detailed metadata of a specific document."
)
def get_document_details(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User '{current_user.username}' requested details for document {id}.")
    doc = DocumentService.get_document_by_id(db, id, current_user.id)
    if not doc:
        logger.warning(f"Document {id} not found or access denied for user '{current_user.username}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    return doc

@router.delete(
    "/{id}", 
    response_model=MessageResponse,
    summary="Delete a document",
    description="Deletes a document record from SQLite, removes the local file from disk, and rebuilds the FAISS vector database."
)
def delete_document(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"User '{current_user.username}' requested deletion of document {id}.")
    success = DocumentService.delete_document(db, id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or permission denied."
        )
    return {"message": "Document deleted successfully and index updated."}
