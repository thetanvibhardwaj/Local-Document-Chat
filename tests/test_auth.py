import pytest
from fastapi.testclient import TestClient

def test_user_flow(client: TestClient):
    """
    Tests the complete user lifecycle: Registration, Login, Profile access,
    and Logout invalidation.
    """
    username = "test_user_pytest"
    password = "secure_password_123"
    
    # 1. Register User
    reg_response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password}
    )
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert reg_data["username"] == username
    assert "id" in reg_data
    
    # 2. Block Duplicate Registration
    dup_response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password}
    )
    assert dup_response.status_code == 400
    
    # 3. Fail Login with Invalid Credentials
    bad_login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "wrong_password"}
    )
    assert bad_login.status_code == 401
    
    # 4. Successful Login & JWT Retrieve
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    token = token_data["access_token"]
    
    # 5. Access Profile with JWT Header
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = client.get("/api/auth/profile", headers=headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    assert profile_data["username"] == username
    assert profile_data["total_documents"] == 0
    assert profile_data["total_chats"] == 0
    
    # 6. Access Profile without Authentication Headers (Should fail)
    fail_profile = client.get("/api/auth/profile")
    assert fail_profile.status_code == 401
    
    # 7. Log out (Invalidate Token)
    logout_response = client.post("/api/auth/logout", headers=headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Successfully logged out."
    
    # 8. Try to reuse the logged-out token (Should fail)
    reuse_token = client.get("/api/auth/profile", headers=headers)
    assert reuse_token.status_code == 401
