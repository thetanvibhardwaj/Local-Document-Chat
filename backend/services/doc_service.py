import os
import uuid
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.models import Document, EmbeddingsMetadata
from backend.rag.loader import DocumentLoader
from backend.rag.text_processor import TextProcessor
from backend.rag.vector_store import VectorStoreManager
from backend.utils.config import settings
from backend.utils.logger import logger
from langchain_core.documents import Document as LangChainDocument

class DocumentService:
    # Whitelist of approved extensions
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    @classmethod
    def validate_file(cls, file: UploadFile) -> str:
        """
        Verify file format extension. Raises bad request if invalid.
        """
        filename = file.filename or ""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            logger.warning(f"File upload blocked: Unsupported extension '{ext}' in '{filename}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: PDF, DOCX, TXT."
            )
        return ext

    @classmethod
    def upload_and_process_document(cls, db: Session, file: UploadFile, user_id: int) -> Document:
        """
        Handles document uploading:
        1. Validates details.
        2. Writes to the local folder.
        3. Parses content into chunks.
        4. Saves chunk references in SQLAlchemy.
        5. Saves vector embeddings in local FAISS store.
        """
        ext = cls.validate_file(file)
        
        # Create a unique storage filename to avoid overrides or directory traversal attacks
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        os.makedirs(settings.upload_dir, exist_ok=True)
        filepath = os.path.join(settings.upload_dir, unique_filename)
        
        # Save file to disk while validating size threshold
        size_bytes = 0
        try:
            with open(filepath, "wb") as f:
                while content := file.file.read(1024 * 1024):  # 1MB buffer
                    size_bytes += len(content)
                    if size_bytes > settings.max_upload_size_mb * 1024 * 1024:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File size exceeds maximum threshold of {settings.max_upload_size_mb}MB."
                        )
                    f.write(content)
        except HTTPException:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
        except Exception as e:
            logger.error(f"Failed writing upload file to storage: {e}", exc_info=True)
            if os.path.exists(filepath):
                os.remove(filepath)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed saving uploaded file to local filesystem."
            )

        # 1. Create a DB record in PENDING state
        db_doc = Document(
            filename=file.filename,
            filepath=filepath,
            file_type=ext,
            size_bytes=size_bytes,
            embedding_status="PENDING",
            user_id=user_id
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        # 2. Process RAG pipeline indexing
        try:
            logger.info(f"Parsing document text: {filepath}...")
            raw_docs = DocumentLoader.load(filepath)
            
            logger.info(f"Chunking document content...")
            chunks = TextProcessor.split_documents(raw_docs)
            
            if not chunks:
                raise ValueError("No readable text found in document.")
                
            # Prepare metadata and database elements
            db_chunks = []
            langchain_chunks = []
            
            for idx, chunk in enumerate(chunks):
                page_num = chunk.metadata.get("page")
                
                # SQLAlchemy DB schema meta entry
                db_chunk = EmbeddingsMetadata(
                    document_id=db_doc.id,
                    chunk_index=idx,
                    chunk_text=chunk.page_content,
                    page_number=page_num
                )
                db_chunks.append(db_chunk)
                
                # LangChain Document object for vector database mapping
                chunk.metadata["document_id"] = db_doc.id
                chunk.metadata["filename"] = db_doc.filename
                langchain_chunks.append(chunk)

            # Save chunks to SQLite for fast deletion rebuilds
            db.add_all(db_chunks)
            
            # Save into FAISS vector store
            logger.info("==============")
            logger.info(f"Saving {len(langchain_chunks)} chunks")
            logger.info(f"Vector directory = {settings.vector_store_dir}")
            logger.info("==============")
            VectorStoreManager.save_or_update_index(user_id, langchain_chunks)
            
            # Commit processed results
            db_doc.embedding_status = "PROCESSED"
            db_doc.chunk_count = len(chunks)
            db.commit()
            db.refresh(db_doc)
            logger.info(f"Document {db_doc.id} ('{db_doc.filename}') indexed successfully.")
            
        except Exception as e:
            logger.error(f"RAG processing failed for document {db_doc.id}: {e}", exc_info=True)
            db_doc.embedding_status = "FAILED"
            db.commit()
            
            # Delete physical file on failure
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as cleanup_err:
                    logger.error(f"Cleanup failed for file '{filepath}': {cleanup_err}")
                    
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document parsing/indexing failed: {str(e)}"
            )
            
        return db_doc

    @classmethod
    def delete_document(cls, db: Session, doc_id: int, user_id: int) -> bool:
        """
        Delete document record, delete local source file, and rebuild
        the FAISS index from remaining user documents.
        """
        db_doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
        if not db_doc:
            logger.warning(f"Delete failed: Document {doc_id} not found for user {user_id}.")
            return False
            
        # 1. Delete source file from uploads folder
        filepath = db_doc.filepath
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted source file '{filepath}' from uploads.")
        except Exception as e:
            logger.error(f"Failed deleting upload file '{filepath}' on disk: {e}")
            
        # 2. Delete database record (will automatically cascade delete metadata and chat logs)
        db.delete(db_doc)
        db.commit()
        logger.info(f"Successfully deleted DB records for document {doc_id}.")
        
        # 3. Retrieve chunks of remaining documents for this user
        remaining_db_chunks = db.query(EmbeddingsMetadata).join(Document).filter(
            Document.user_id == user_id
        ).order_by(EmbeddingsMetadata.document_id, EmbeddingsMetadata.chunk_index).all()
        
        # 4. Map back to LangChain Documents for FAISS index rebuild
        remaining_chunks = []
        for chunk in remaining_db_chunks:
            doc_name = db.query(Document.filename).filter(Document.id == chunk.document_id).scalar() or "Unknown"
            doc_lc = LangChainDocument(
                page_content=chunk.chunk_text,
                metadata={
                    "document_id": chunk.document_id,
                    "filename": doc_name,
                    "page": chunk.page_number
                }
            )
            remaining_chunks.append(doc_lc)
            
        # 5. Rebuild the FAISS index (or delete it if no files are left)
        VectorStoreManager.rebuild_index(user_id, remaining_chunks)
        return True

    @staticmethod
    def get_user_documents(db: Session, user_id: int) -> List[Document]:
        """Fetch all documents belonging to a specific user."""
        return db.query(Document).filter(Document.user_id == user_id).all()

    @staticmethod
    def get_document_by_id(db: Session, doc_id: int, user_id: int) -> Optional[Document]:
        """Fetch document details by id, verifying user ownership."""
        return db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
