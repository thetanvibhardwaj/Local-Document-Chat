"""
DocuChat AI - Streamlit Frontend
---------------------------------
A pure API client for the FastAPI backend: every action here calls one of
the REST endpoints (/register, /login, /upload, /chat, etc). No business
logic lives in this file, so it can be swapped for a React frontend later
without touching the backend at all.
"""
import os
import time

import requests
import streamlit as st

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="DocuChat AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Theme: luxury black & grey (dark default, light variant toggle)
# --------------------------------------------------------------------------
DARK_CSS = """
<style>
    .stApp { background-color: #0E0E10; color: #E8E6E3; }
    section[data-testid="stSidebar"] { background-color: #16161A; border-right: 1px solid #2A2A2E; }
    .docuchat-title { color: #C9A961; font-weight: 700; letter-spacing: 1px; }
    .docuchat-subtitle { color: #9A9A9E; font-size: 0.9rem; }
    .stChatMessage { background-color: #1A1A1D; border: 1px solid #2A2A2E; border-radius: 12px; }
    .source-badge {
        display: inline-block; background-color: #2A2A2E; color: #C9A961;
        border-radius: 6px; padding: 2px 10px; margin: 2px 4px 2px 0;
        font-size: 0.78rem; border: 1px solid #3A3A3E;
    }
    .stButton>button {
        background-color: #1A1A1D; color: #C9A961; border: 1px solid #C9A961;
        border-radius: 8px;
    }
    .stButton>button:hover { background-color: #C9A961; color: #0E0E10; }
    div[data-testid="stFileUploaderDropzone"] {
        background-color: #1A1A1D; border: 1.5px dashed #C9A961; border-radius: 12px;
    }
</style>
"""

LIGHT_CSS = """
<style>
    .stApp { background-color: #F5F5F4; color: #1C1C1E; }
    section[data-testid="stSidebar"] { background-color: #EAEAE8; border-right: 1px solid #D8D8D6; }
    .docuchat-title { color: #8A6D3B; font-weight: 700; letter-spacing: 1px; }
    .docuchat-subtitle { color: #6A6A6E; font-size: 0.9rem; }
    .stChatMessage { background-color: #FFFFFF; border: 1px solid #E0E0DE; border-radius: 12px; }
    .source-badge {
        display: inline-block; background-color: #EFE9DC; color: #8A6D3B;
        border-radius: 6px; padding: 2px 10px; margin: 2px 4px 2px 0;
        font-size: 0.78rem; border: 1px solid #D8C9A8;
    }
    .stButton>button {
        background-color: #FFFFFF; color: #8A6D3B; border: 1px solid #8A6D3B;
        border-radius: 8px;
    }
    .stButton>button:hover { background-color: #8A6D3B; color: #FFFFFF; }
    div[data-testid="stFileUploaderDropzone"] {
        background-color: #FFFFFF; border: 1.5px dashed #8A6D3B; border-radius: 12px;
    }
</style>
"""

# --------------------------------------------------------------------------
# Session state defaults
# --------------------------------------------------------------------------
defaults = {
    "theme": "dark",
    "token": None,
    "user": None,
    "current_session_id": None,
    "messages": [],  # local mirror of the active session's messages
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.markdown(DARK_CSS if st.session_state.theme == "dark" else LIGHT_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------
def api_headers() -> dict:
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def api_post(path: str, json: dict | None = None, files=None, data=None):
    return requests.post(f"{BACKEND_API_URL}{path}", json=json, files=files, data=data, headers=api_headers())


def api_get(path: str, params: dict | None = None):
    return requests.get(f"{BACKEND_API_URL}{path}", params=params, headers=api_headers())


def api_delete(path: str):
    return requests.delete(f"{BACKEND_API_URL}{path}", headers=api_headers())


def type_out(text: str, placeholder) -> None:
    """Lightweight typing animation for the assistant's answer."""
    rendered = ""
    for word in text.split(" "):
        rendered += word + " "
        placeholder.markdown(rendered + "▌")
        time.sleep(0.012)
    placeholder.markdown(rendered)


# --------------------------------------------------------------------------
# Auth screens (register / login)
# --------------------------------------------------------------------------
def render_auth_screen() -> None:
    st.markdown('<h1 class="docuchat-title">📄 DocuChat AI</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="docuchat-subtitle">Enterprise document intelligence, powered by Retrieval-Augmented Generation.</p>',
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            resp = api_post("/login", json={"username": username, "password": password})
            if resp.status_code == 200:
                payload = resp.json()
                st.session_state.token = payload["access_token"]
                st.session_state.user = payload["user"]
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Login failed."))

    with tab_register:
        with st.form("register_form"):
            reg_username = st.text_input("Choose a username")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Choose a password", type="password", help="Min 8 chars, 1 digit, 1 uppercase")
            reg_submitted = st.form_submit_button("Create account", use_container_width=True)
        if reg_submitted:
            resp = api_post(
                "/register",
                json={"username": reg_username, "email": reg_email, "password": reg_password},
            )
            if resp.status_code == 201:
                st.success("Account created! Please log in from the Login tab.")
            else:
                detail = resp.json().get("detail", "Registration failed.")
                st.error(detail)


# --------------------------------------------------------------------------
# Sidebar: theme toggle, document manager, session list
# --------------------------------------------------------------------------
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(f'<h2 class="docuchat-title">DocuChat AI</h2>', unsafe_allow_html=True)
        st.caption(f"Signed in as **{st.session_state.user['username']}**")

        theme_choice = st.radio("Theme", ["Dark", "Light"], horizontal=True,
                                 index=0 if st.session_state.theme == "dark" else 1)
        new_theme = "dark" if theme_choice == "Dark" else "light"
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.rerun()

        if st.button("Log out", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.messages = []
            st.session_state.current_session_id = None
            st.rerun()

        st.divider()
        st.subheader("📁 Documents")

        uploaded = st.file_uploader(
            "Drag and drop a document", type=["pdf", "docx", "txt", "md"], key="uploader"
        )
        if uploaded is not None and st.button("Upload & Index", use_container_width=True):
            with st.spinner(f"Indexing {uploaded.name}..."):
                files = {"file": (uploaded.name, uploaded.getvalue())}
                resp = api_post("/documents/upload", files=files)
            if resp.status_code == 201:
                st.success(f"{uploaded.name} indexed successfully.")
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Upload failed."))

        docs_resp = api_get("/documents")
        if docs_resp.status_code == 200:
            documents = docs_resp.json()["documents"]
            for doc in documents:
                col1, col2, col3 = st.columns([5, 1, 1])
                status_icon = {"ready": "✅", "processing": "⏳", "failed": "❌"}.get(doc["status"], "•")
                col1.markdown(f"{status_icon} {doc['filename']}  \n`{doc['total_chunks']} chunks`")
                if col2.button("🔄", key=f"reindex_{doc['id']}", help="Re-index"):
                    api_post(f"/documents/{doc['id']}/reindex")
                    st.rerun()
                if col3.button("🗑️", key=f"delete_{doc['id']}", help="Delete"):
                    api_delete(f"/documents/{doc['id']}")
                    st.rerun()

        st.divider()
        st.subheader("💬 Chat Sessions")

        if st.button("+ New Session", use_container_width=True):
            resp = api_post("/chat/sessions", json={"session_name": "New Chat"})
            if resp.status_code == 201:
                st.session_state.current_session_id = resp.json()["id"]
                st.session_state.messages = []
                st.rerun()

        sessions_resp = api_get("/chat/sessions")
        if sessions_resp.status_code == 200:
            for session in sessions_resp.json():
                col1, col2 = st.columns([5, 1])
                label = session["session_name"] or "New Chat"
                if col1.button(label, key=f"session_{session['id']}", use_container_width=True):
                    st.session_state.current_session_id = session["id"]
                    history_resp = api_get("/chat/history", params={"session_id": session["id"]})
                    st.session_state.messages = []
                    if history_resp.status_code == 200:
                        for item in history_resp.json():
                            st.session_state.messages.append({"role": "user", "content": item["question"]})
                            st.session_state.messages.append({"role": "assistant", "content": item["answer"], "sources": []})
                    st.rerun()
                if col2.button("✕", key=f"del_session_{session['id']}"):
                    api_delete(f"/chat/session/{session['id']}")
                    if st.session_state.current_session_id == session["id"]:
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
                    st.rerun()


# --------------------------------------------------------------------------
# Main chat panel
# --------------------------------------------------------------------------
def render_chat() -> None:
    st.markdown('<h1 class="docuchat-title">📄 DocuChat AI</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="docuchat-subtitle">Ask questions about your uploaded documents. Answers are strictly grounded in your files.</p>',
        unsafe_allow_html=True,
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                badges = " ".join(
                    f'<span class="source-badge">📄 {s["filename"]} · chunk #{s["chunk_number"]} · {s["similarity_score"]:.2f}</span>'
                    for s in message["sources"]
                )
                st.markdown(badges, unsafe_allow_html=True)

    question = st.chat_input("Ask a question about your documents...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("Thinking...")
            resp = api_post(
                "/chat",
                json={"question": question, "session_id": st.session_state.current_session_id},
            )
            if resp.status_code == 200:
                payload = resp.json()
                st.session_state.current_session_id = payload["session_id"]
                type_out(payload["answer"], placeholder)
                if payload["sources"]:
                    badges = " ".join(
                        f'<span class="source-badge">📄 {s["filename"]} · chunk #{s["chunk_number"]} · {s["similarity_score"]:.2f}</span>'
                        for s in payload["sources"]
                    )
                    st.markdown(badges, unsafe_allow_html=True)
                st.session_state.messages.append(
                    {"role": "assistant", "content": payload["answer"], "sources": payload["sources"]}
                )
            else:
                error_detail = resp.json().get("detail", "Something went wrong.")
                placeholder.markdown(f"⚠️ {error_detail}")
                st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {error_detail}", "sources": []})


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def main() -> None:
    if not st.session_state.token:
        render_auth_screen()
    else:
        render_sidebar()
        render_chat()


if __name__ == "__main__":
    main()
