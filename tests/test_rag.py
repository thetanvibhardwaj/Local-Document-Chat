import os
import pytest
from langchain_core.documents import Document
from backend.rag.loader import DocumentLoader
from backend.rag.text_processor import TextProcessor
from backend.rag.vector_store import VectorStoreManager

def test_text_cleaning():
    """Verify that multiple tabs, spaces, and excess newlines are collapsed."""
    raw_text = "Hello    World!   \n\n\n\nNew   Paragraph."
    cleaned = TextProcessor.clean_text(raw_text)
    assert cleaned == "Hello World!\n\nNew Paragraph."

def test_text_splitting():
    """Verify that document text is correctly chunked with overlap."""
    doc = Document(page_content="A" * 1500, metadata={"source": "test.txt"})
    chunks = TextProcessor.split_documents([doc], chunk_size=1000, chunk_overlap=100)
    
    # 1500 chars with size 1000 and overlap 100 should result in 2 chunks
    assert len(chunks) == 2
    assert len(chunks[0].page_content) <= 1000
    assert chunks[0].metadata["page"] == 1

def test_local_faiss_lifecycle(tmp_path):
    """
    Verify that FAISS index can be created, saved, retrieved, and rebuilt
    using user isolation directories.
    """
    user_id = 888
    # Point vector store directory to temp directory for testing isolation
    import backend.rag.vector_store as vs
    original_store_dir = vs.settings.vector_store_dir
    vs.settings.vector_store_dir = str(tmp_path)
    
    chunks = [
        Document(
            page_content="Cognify Docs uses LangChain and Uvicorn.",
            metadata={"document_id": 1, "filename": "info.txt", "page": 1}
        ),
        Document(
            page_content="FAISS stores dense vector embeddings locally.",
            metadata={"document_id": 2, "filename": "db.txt", "page": 1}
        )
    ]
    
    try:
        # 1. Index documents
        VectorStoreManager.save_or_update_index(user_id, chunks)
        assert VectorStoreManager.index_exists(user_id) is True
        
        # 2. Get retriever and search for content
        retriever = VectorStoreManager.get_retriever(user_id)
        assert retriever is not None
        
        results = retriever.get_relevant_documents("What stores vector embeddings?")
        assert len(results) > 0
        assert "FAISS" in results[0].page_content
        
        # 3. Filtered retrieval by document ID
        filtered_retriever = VectorStoreManager.get_retriever(user_id, document_id=1)
        filtered_results = filtered_retriever.get_relevant_documents("vector embeddings")
        # Should only retrieve chunk from doc_id 1 since it's filtered
        for doc in filtered_results:
            assert doc.metadata["document_id"] == 1
            
        # 4. Rebuild index (e.g. deleting document 2 chunks)
        remaining = [chunks[0]]
        VectorStoreManager.rebuild_index(user_id, remaining)
        
        rebuilt_retriever = VectorStoreManager.get_retriever(user_id)
        rebuilt_results = rebuilt_retriever.get_relevant_documents("embeddings")
        # Should find nothing or fallback since doc_id 2 chunks were deleted
        for doc in rebuilt_results:
            assert "FAISS" not in doc.page_content
            
    finally:
        # Reset settings
        vs.settings.vector_store_dir = original_store_dir
