import io
import pytest
from fastapi.testclient import TestClient

def test_health_check_endpoint(client: TestClient):
    """Verify that root router returns healthy service status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "application" in data

def test_api_document_lifecycle(client: TestClient, tmp_path):
    """
    Tests the complete API document pipeline: Register/Login, upload file,
    list files, inspect file detail metadata, and delete file.
    """
    # Override settings for vector storage to write to a temp directory during test run
    import backend.services.doc_service as ds
    import backend.rag.vector_store as vs
    
    original_upload_dir = ds.settings.upload_dir
    original_vector_dir = vs.settings.vector_store_dir
    
    ds.settings.upload_dir = str(tmp_path / "uploads")
    vs.settings.vector_store_dir = str(tmp_path / "vectors")
    
    try:
        username = "doc_lifecycle_user"
        password = "testpassword123"
        
        # 1. Register & Login User
        client.post("/api/auth/register", json={"username": username, "password": password})
        login_res = client.post("/api/auth/login", json={"username": username, "password": password})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Upload Document
        file_content = b"FastAPI is a high-performance web framework. Python is used for backend development."
        file_name = "test_api_doc.txt"
        files = {"file": (file_name, io.BytesIO(file_content), "text/plain")}
        
        upload_res = client.post("/api/documents/upload", files=files, headers=headers)
        assert upload_res.status_code == 201
        doc_data = upload_res.json()
        assert doc_data["filename"] == file_name
        assert doc_data["file_type"] == ".txt"
        assert doc_data["embedding_status"] == "PROCESSED"
        doc_id = doc_data["id"]
        
        # 3. Retrieve Documents List
        list_res = client.get("/api/documents", headers=headers)
        assert list_res.status_code == 200
        docs = list_res.json()
        assert len(docs) == 1
        assert docs[0]["filename"] == file_name
        
        # 4. Retrieve Document Details
        detail_res = client.get(f"/api/documents/{doc_id}", headers=headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == doc_id
        
        # 5. Delete Document
        delete_res = client.delete(f"/api/documents/{doc_id}", headers=headers)
        assert delete_res.status_code == 200
        assert "deleted successfully" in delete_res.json()["message"]
        
        # 6. Verify List is Empty
        empty_list_res = client.get("/api/documents", headers=headers)
        assert len(empty_list_res.json()) == 0
        
    finally:
        # Restore configuration paths
        ds.settings.upload_dir = original_upload_dir
        vs.settings.vector_store_dir = original_vector_dir
