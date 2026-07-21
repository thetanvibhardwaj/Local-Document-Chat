"""Tests for the /chat endpoint's grounded-answer behaviour."""


def _auth_headers(client, test_user_payload) -> dict:
    client.post("/api/v1/register", json=test_user_payload)
    login_resp = client.post(
        "/api/v1/login",
        json={"username": test_user_payload["username"], "password": test_user_payload["password"]},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_chat_requires_auth(client):
    resp = client.post("/api/v1/chat", json={"question": "What is the leave policy?"})
    assert resp.status_code == 401


def test_chat_with_no_documents_returns_fallback(client, test_user_payload):
    """
    With no documents uploaded/indexed for this user, the RAG pipeline should
    return the strict 'no relevant information' fallback rather than calling
    Gemini with empty context.
    """
    headers = _auth_headers(client, test_user_payload)
    resp = client.post("/api/v1/chat", json={"question": "What is our vacation policy?"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "couldn't find relevant information" in body["answer"].lower()
    assert body["sources"] == []
