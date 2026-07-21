"""Tests for /register and /login."""


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login(client, test_user_payload):
    register_resp = client.post("/api/v1/register", json=test_user_payload)
    assert register_resp.status_code in (201, 409)  # 409 if already registered from a prior run

    login_resp = client.post(
        "/api/v1/login",
        json={"username": test_user_payload["username"], "password": test_user_payload["password"]},
    )
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert "access_token" in body
    assert body["user"]["username"] == test_user_payload["username"]


def test_login_invalid_credentials(client):
    resp = client.post("/api/v1/login", json={"username": "nonexistent_user", "password": "wrong"})
    assert resp.status_code == 401
