"""Tests for document upload/list/delete endpoints."""
import io


def _auth_headers(client, test_user_payload) -> dict:
    client.post("/api/v1/register", json=test_user_payload)
    login_resp = client.post(
        "/api/v1/login",
        json={"username": test_user_payload["username"], "password": test_user_payload["password"]},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_auth(client):
    files = {"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
    resp = client.post("/api/v1/documents/upload", files=files)
    assert resp.status_code == 401


def test_upload_rejects_unsupported_extension(client, test_user_payload):
    headers = _auth_headers(client, test_user_payload)
    files = {"file": ("malware.exe", io.BytesIO(b"binary"), "application/octet-stream")}
    resp = client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert resp.status_code == 400


def test_list_documents_empty_or_populated(client, test_user_payload):
    headers = _auth_headers(client, test_user_payload)
    resp = client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    assert "documents" in resp.json()
