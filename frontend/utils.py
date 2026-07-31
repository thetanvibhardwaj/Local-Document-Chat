import os
import httpx
import streamlit as st
from typing import Dict, List, Any, Optional, Tuple

API_BASE_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

def get_headers() -> Dict[str, str]:
    """Helper to attach bearer authorization token to request headers."""
    headers = {}
    if "token" in st.session_state and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return headers

def make_request(
    method: str, 
    endpoint: str, 
    json_data: Optional[Dict[str, Any]] = None, 
    files: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Tuple[int, Any]:
    """
    Unified HTTP helper client using httpx.
    Returns a tuple of (status_code, response_data).
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_headers()
    
    try:
        with httpx.Client(timeout=120.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = client.post(url, headers=headers, json=json_data, files=files, params=params)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            # Try to decode JSON, fallback to raw text if not JSON
            try:
                data = response.json()
            except Exception:
                # If we get a 502/503 from Render (e.g. server is waking up from sleep)
                if response.status_code in (502, 503, 504):
                    data = {"detail": "Backend server is waking up (or unreachable). Please wait 30-50 seconds and try again."}
                else:
                    data = {"detail": f"Server returned an unexpected response (Status {response.status_code})."}
                
            return response.status_code, data
    except httpx.NetworkError:
        return 503, {"detail": "Backend server is unreachable. Please verify the URL and ensure the server is running."}
    except httpx.TimeoutException:
        return 504, {"detail": "Request to backend timed out. The server might be waking up from sleep, please try again."}
    except Exception as e:
        return 500, {"detail": f"An unexpected error occurred: {str(e)}"}

# --- Authentication Helpers ---

def api_register(username: str, password: str) -> Tuple[bool, str]:
    """Registers a new user. Returns (success, message_or_error)."""
    status, data = make_request("POST", "/api/auth/register", json_data={"username": username, "password": password})
    if status == 201:
        return True, "Registration successful! You can now log in."
    else:
        detail = data.get("detail", "Registration failed.") if isinstance(data, dict) else data
        return False, detail

def api_login(username: str, password: str) -> Tuple[bool, str]:
    """Logs in user, saving JWT token in streamlit session state. Returns (success, token_or_error)."""
    status, data = make_request("POST", "/api/auth/login", json_data={"username": username, "password": password})
    if status == 200:
        st.session_state.token = data["access_token"]
        st.session_state.username = username
        st.session_state.logged_in = True
        return True, "Login successful."
    else:
        detail = data.get("detail", "Invalid username or password.") if isinstance(data, dict) else data
        return False, detail

def api_logout() -> None:
    """Logs out user and invalidates backend session database entry."""
    if "token" in st.session_state and st.session_state.token:
        # Inform backend of session invalidation
        make_request("POST", "/api/auth/logout")
    
    # Reset local Streamlit states
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.logged_in = False
    if "history" in st.session_state:
        del st.session_state.history

def api_get_profile() -> Tuple[bool, Dict[str, Any]]:
    """Gets current user's profile statistics."""
    status, data = make_request("GET", "/api/auth/profile")
    if status == 200:
        return True, data
    return False, data

# --- Document Management Helpers ---

def api_list_documents() -> List[Dict[str, Any]]:
    """Lists all files uploaded by the authenticated user."""
    status, data = make_request("GET", "/api/documents")
    if status == 200:
        return data
    return []

def api_upload_document(filename: str, file_bytes: bytes) -> Tuple[bool, str]:
    """Uploads file bytes to the document ingestion pipeline."""
    files = {"file": (filename, file_bytes, "application/octet-stream")}
    status, data = make_request("POST", "/api/documents/upload", files=files)
    if status == 201:
        return True, "Document uploaded and indexed successfully!"
    else:
        detail = data.get("detail", "Upload failed.") if isinstance(data, dict) else data
        return False, detail

def api_delete_document(doc_id: int) -> Tuple[bool, str]:
    """Deletes a document and triggers index reconstruction."""
    status, data = make_request("DELETE", f"/api/documents/{doc_id}")
    if status == 200:
        return True, "Document deleted successfully."
    else:
        detail = data.get("detail", "Deletion failed.") if isinstance(data, dict) else data
        return False, detail

# --- RAG Chat Helpers ---

def api_chat(question: str, document_id: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
    """Submits query to RAG agent. Returns (success, payload)."""
    payload = {"question": question}
    if document_id is not None:
        payload["document_id"] = document_id
        
    status, data = make_request("POST", "/api/chat", json_data=payload)
    if status == 200:
        return True, data
    else:
        detail = data.get("detail", "RAG query failed.") if isinstance(data, dict) else data
        return False, {"answer": f"Error: {detail}", "citations": []}

def api_get_history(q: Optional[str] = None, document_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Gets previous conversation logs, supporting queries and filters."""
    params = {}
    if q:
        params["q"] = q
    if document_id is not None:
        params["document_id"] = document_id
        
    status, data = make_request("GET", "/api/chat/history", params=params)
    if status == 200:
        return data
    return []
