import os
import sys
import time
import base64
import io
import csv
import html as _html

# Safeguard: Resolve pathing issues if running directly from within the frontend directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import streamlit.components.v1 as components
import datetime
from frontend.utils import (
    api_register,
    api_login,
    api_logout,
    api_get_profile,
    api_list_documents,
    api_upload_document,
    api_delete_document,
    api_chat,
    api_get_history
)

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Cognify Docs | AI Document Q&A",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# SESSION STATE
# ============================================================
_defaults = {
    "logged_in": False,
    "token": None,
    "username": None,
    "current_page": "Dashboard",
    "chat_history_state": [],
    "theme": "dark",
    "chat_response_times": [],
    "pending_chat_doc_id": "__unset__",
    "doc_manager_prefill": "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

NAV_ITEMS = [
    ("Dashboard", "📊"),
    ("Document Manager", "📂"),
    ("Chat Arena", "💬"),
    ("History Explorer", "🔎"),
    ("Profile & Settings", "⚙️"),
]

# ============================================================
# THEME ENGINE — variables injected server-side, remembered in session_state
# ============================================================
THEMES = {
    "dark": {
        "bg": "#090D0C", "header": "#0E1412", "sidebar": "#080B0A", "card": "#131C19",
        "text": "#F1F5F3", "text-muted": "#8E9F9A", "border": "rgba(139,168,136,.14)",
        "accent": "#8BA888", "secondary": "#A3C19E",
    },
    "light": {
        "bg": "#F4F7F5", "header": "#FFFFFF", "sidebar": "#FFFFFF", "card": "#FFFFFF",
        "text": "#1C2421", "text-muted": "#5E6E69", "border": "#E1E8E4",
        "accent": "#4F644D", "secondary": "#7FA67A",
    },
}


def _inject_styles():
    theme_vars = THEMES[st.session_state.theme]
    root_vars = "\n".join([f"--{k}: {v};" for k, v in theme_vars.items()])
    st.markdown(f"<style>:root {{ {root_vars} }}</style>", unsafe_allow_html=True)

    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("Custom CSS file not found. Falling back to default styles.")


# ============================================================
# ICON HELPERS (inline SVG, stroke-based, currentColor)
# ============================================================
def svg_icon(path_d, size=18, view_box="0 0 24 24"):
    return (f'<svg width="{size}" height="{size}" viewBox="{view_box}" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round">{path_d}</svg>')


ICON_SUN = svg_icon('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/>')
ICON_MOON = svg_icon('<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>')
ICON_SEARCH = svg_icon('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>')
ICON_LOGOUT = svg_icon('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>')
ICON_FOLDER = svg_icon('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>')
ICON_CHAT = svg_icon('<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/>')


def format_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.2f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.2f} MB"


def _initials(name: str) -> str:
    if not name:
        return "?"
    parts = [p for p in name.replace("_", " ").replace(".", " ").split(" ") if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


# ============================================================
# HEADER
# ============================================================
def render_header():
    with st.container(key="app_header"):
        col_brand, col_search, col_user = st.columns([2.2, 3, 2.4], vertical_alignment="center")

        with col_brand:
            st.markdown(
                f"""
                <div class="header-brand">
                    <p class="brand-title"><span style="font-weight: 800; letter-spacing: 0.5px;">COGNIFY</span> <span style="font-weight: 300; opacity: 0.8;">DOCS</span></p>
                    <p class="brand-subtitle">Enterprise RAG Knowledge Platform</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_search:
            with st.form("global_search_form", clear_on_submit=False, border=False):
                sc1, sc2 = st.columns([5, 1])
                with sc1:
                    query = st.text_input(
                        "Global search", placeholder="Search documents... (Ctrl+K)",
                        label_visibility="collapsed", key="global_search_input",
                    )
                with sc2:
                    go = st.form_submit_button("Go", use_container_width=True)
                if go and query.strip():
                    _handle_global_search(query.strip())

        with col_user:
            uname = st.session_state.get("username") or "User"
            # 3 tight sub-columns: avatar | username | logout btn
            ua, ub, uc = st.columns([0.55, 1.4, 1.1])
            with ua:
                st.markdown(
                    f'<div class="header-avatar">{_initials(uname)}</div>',
                    unsafe_allow_html=True,
                )
            with ub:
                st.markdown(
                    f'<div class="header-username">{_html.escape(uname)}</div>',
                    unsafe_allow_html=True,
                )
            with uc:
                if st.button("⏻ Logout", key="header_logout", use_container_width=True):
                    api_logout()
                    st.rerun()


def _handle_global_search(query: str):
    """Lightweight client-side routing: matches nav pages first, then document names.
    Uses only already-available endpoints (no new backend calls added)."""
    q = query.lower()
    page_keywords = {
        "Dashboard": ["dashboard", "home", "overview"],
        "Document Manager": ["document", "doc", "upload", "file"],
        "Chat Arena": ["chat", "ask", "query", "qa"],
        "History Explorer": ["history", "past", "log"],
        "Profile & Settings": ["setting", "profile", "account"],
    }
    for page, keywords in page_keywords.items():
        if any(k in q for k in keywords):
            st.session_state.current_page = page
            st.rerun()
            return

    docs = api_list_documents()
    matches = [d for d in docs if q in d["filename"].lower()]
    if matches:
        st.session_state.current_page = "Document Manager"
        st.session_state.doc_manager_prefill = query
        st.rerun()
    else:
        st.toast(f"No matches found for '{query}'", icon="🔍")


# ============================================================
# SIDEBAR
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-logo">
                <div class="logo-mark">📂</div>
                <p class="logo-name">COGNIFY DOCS</p>
                <span class="logo-tag">⚡ {st.session_state.username}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sidebar-section-label">Navigation</div>', unsafe_allow_html=True)
        for label, emoji in NAV_ITEMS:
            is_active = st.session_state.current_page == label
            if st.button(
                f"{emoji}  {label}",
                key=f"nav_{label}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.current_page = label
                st.rerun()

        st.markdown(
            """
            <div class="sidebar-footer-card">
                Cognify Docs v1.0.0<br/>B.Tech Major Project © 2026
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# FOOTER
# ============================================================
def render_footer():
    with st.container(key="app_footer"):
        st.markdown(
            """<div class="footer-bottom">
                🗂️ <span>Cognify Docs v1.0.0</span> &nbsp;·&nbsp;
                RAG Knowledge Platform &nbsp;·&nbsp;
                FastAPI · LangChain · FAISS · Gemini &nbsp;·&nbsp;
                <span>● Operational</span> &nbsp;·&nbsp;
                © 2026 B.Tech Major Project
            </div>""",
            unsafe_allow_html=True,
        )


# ============================================================
# AUTH PAGE
# ============================================================
def render_auth_page():
    # ── Inject full-page Three.js animated background ─────────────────────
    bg_path = os.path.join(os.path.dirname(__file__), "login_bg.html")
    if os.path.exists(bg_path):
        with open(bg_path, "r", encoding="utf-8") as f:
            bg_html = f.read()
        # Embed as fixed-position full-viewport iframe behind Streamlit UI
        import urllib.parse
        encoded = urllib.parse.quote(bg_html)
        st.markdown(
            f'<iframe src="data:text/html;charset=utf-8,{encoded}" '
            f'style="position:fixed;top:0;left:0;width:100vw;height:100vh;'
            f'border:none;z-index:0;pointer-events:none;" '
            f'sandbox="allow-scripts"></iframe>',
            unsafe_allow_html=True,
        )

    # ── Glassmorphism overlay for the login card ────────────────────────────
    st.markdown("""
    <style>
    /* Full-page dark background so Three.js shows through */
    .stApp { background: transparent !important; }
    [data-testid="stAppViewContainer"] > .main { background: transparent !important; }
    [data-testid="stAppViewContainer"] { background: #0D1117 !important; }

    /* Glassmorphism login card */
    div[class*="cog-card"].fade-in,
    .cog-card.fade-in {
        background: rgba(13,17,23,0.72) !important;
        border: 1px solid rgba(6,182,212,0.18) !important;
        backdrop-filter: blur(24px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
        box-shadow:
            0 0 0 1px rgba(6,182,212,0.08),
            0 24px 60px rgba(0,0,0,0.55),
            0 0 40px rgba(124,58,237,0.08) !important;
    }
    /* Tab styling for login/register */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
    }
    /* Brand title glow on auth page */
    .brand-title { text-shadow: 0 0 40px rgba(6,182,212,0.3); }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:right;padding:56px 12% 28px 0;">
            <p class="brand-title" style="font-size:40px;justify-content:flex-end;">🚀 Cognify Docs</p>
            <p class="brand-subtitle" style="font-size:14px;">AI-Powered Local Document Intelligence Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1.1, 1.3, 0.4])
    with col2:
        tab_login, tab_register = st.tabs(["🔐 Login", "✨ Register"])

        with tab_login:
            st.markdown('<div class="cog-card fade-in">', unsafe_allow_html=True)
            st.markdown('<h3 style="text-align:center;">Welcome Back 👋</h3>', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit = st.form_submit_button("🚀 Sign In", use_container_width=True)
                if submit:
                    if not username or not password:
                        st.error("Please fill in all fields.")
                    else:
                        success, message = api_login(username, password)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_register:
            st.markdown('<div class="cog-card fade-in">', unsafe_allow_html=True)
            st.markdown('<h3 style="text-align:center;">Create Your Account ✨</h3>', unsafe_allow_html=True)
            with st.form("register_form"):
                reg_username = st.text_input("Choose Username", placeholder="Minimum 3 characters")
                reg_password = st.text_input("Choose Password", type="password", placeholder="Minimum 6 characters")
                submit_reg = st.form_submit_button("✨ Create Account", use_container_width=True)
                if submit_reg:
                    if len(reg_username) < 3:
                        st.error("Username must be at least 3 characters.")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        success, message = api_register(reg_username, reg_password)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
            st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# DASHBOARD
# ============================================================
def render_dashboard():
    st.markdown(
        f"""
        <div class="cog-hero fade-in">
            <div class="hero-eyebrow">Welcome back</div>
            <h1>👋 {st.session_state.get("username", "User")}</h1>
            <p>AI-Powered Local Document Chat System using Retrieval-Augmented Generation (RAG)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    success, profile_data = api_get_profile()
    if not success:
        st.error("Failed to load user profile statistics.")
        return

    avg_response = "—"
    if st.session_state.chat_response_times:
        avg_response = f"{sum(st.session_state.chat_response_times) / len(st.session_state.chat_response_times):.1f}s"

    kpis = [
        ("📄", "Documents", profile_data.get("total_documents", 0)),
        ("💬", "Chats", profile_data.get("total_chats", 0)),
        ("💾", "Storage", format_size(profile_data.get("storage_used_bytes", 0))),
        ("⚡", "Avg Response Time", avg_response),
    ]
    cols = st.columns(4)
    for col, (emoji, label, value) in zip(cols, kpis):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card fade-in">
                    <div class="kpi-icon">{emoji}</div>
                    <div>
                        <div class="kpi-value">{value}</div>
                        <div class="kpi-label">{label}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.5, 1])

    with left:
        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">📁 Recent Uploaded Documents</p>', unsafe_allow_html=True)
        docs = api_list_documents()
        if not docs:
            st.info("No documents uploaded yet. Go to Document Manager to upload.")
        else:
            docs_sorted = sorted(docs, key=lambda x: x["upload_date"], reverse=True)[:5]
            for doc in docs_sorted:
                date_str = datetime.datetime.fromisoformat(doc["upload_date"]).strftime("%b %d, %Y %H:%M")
                st.markdown(
                    f"""
                    <div class="doc-card">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <div class="doc-icon">📄</div>
                            <div>
                                <div class="doc-name">{doc['filename']}</div>
                                <div class="doc-meta">{doc['file_type'].upper()} • {format_size(doc['size_bytes'])}</div>
                            </div>
                        </div>
                        <span class="cog-badge badge-purple">{date_str}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">🕘 Recent Activity Timeline</p>', unsafe_allow_html=True)
        recent_history = api_get_history()[:4]
        if not recent_history:
            st.info("No chat activity yet.")
        else:
            st.markdown('<div class="timeline-wrap">', unsafe_allow_html=True)
            for item in recent_history:
                ts = datetime.datetime.fromisoformat(item["timestamp"]).strftime("%b %d, %H:%M")
                st.markdown(
                    f"""
                    <div class="timeline-item">
                        <div class="timeline-dot"></div>
                        <div style="font-size:12px;color:var(--text-muted);">{ts}</div>
                        <div style="font-size:13.5px;font-weight:600;">{item['question']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">🧠 AI Pipeline</p>', unsafe_allow_html=True)
        steps = ["PDF", "Text Extraction", "Chunking", "Embeddings", "FAISS", "Gemini", "Answer"]
        track_html = '<div class="pipeline-track">'
        for i, s in enumerate(steps):
            track_html += f'<span class="pipeline-step">{s}</span>'
            if i < len(steps) - 1:
                track_html += '<span class="pipeline-arrow">→</span>'
        track_html += "</div>"
        st.markdown(track_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">🩺 System Health</p>', unsafe_allow_html=True)

        backend_up = True  # profile call above succeeded, so API + auth layer responded
        db_up = success
        docs_probe = api_list_documents()
        faiss_up = any(d.get("embedding_status") == "PROCESSED" for d in docs_probe) if docs_probe else True
        gemini_up = True
        if st.session_state.chat_history_state:
            last_ai = [m for m in st.session_state.chat_history_state if m["role"] == "ai"]
            if last_ai and last_ai[-1]["text"].startswith("Error:"):
                gemini_up = False

        health = [
            ("Backend (FastAPI)", backend_up),
            ("Database (SQLite)", db_up),
            ("Gemini API", gemini_up),
            ("FAISS Vector Store", faiss_up),
        ]
        for name, ok in health:
            dot_class = "up" if ok else "down"
            status_text = "Operational" if ok else "Unavailable"
            st.markdown(
                f"""
                <div class="system-health-row">
                    <span><span class="status-dot {dot_class}"></span>{name}</span>
                    <span class="cog-badge {'badge-green' if ok else 'badge-red'}">{status_text}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# DOCUMENT MANAGER
# ============================================================
def render_doc_manager():
    st.markdown('<h2 style="font-weight:800;">📂 Document Manager</h2>', unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 1.8])

    with col1:
        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">📤 Upload New Document</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drag & drop or browse — PDF, DOCX or TXT",
            type=["pdf", "docx", "txt"],
            help="Max size 10MB. Content will be immediately processed.",
        )
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            size_mb = len(file_bytes) / (1024 * 1024)
            if size_mb > 10:
                st.error("File exceeds 10MB limit.")
            else:
                if st.button("🚀 Process File", help="Ingest file contents into RAG vector store"):
                    with st.spinner("🔄 Processing document pipeline (Extracting, Chunking, Embedding)..."):
                        success, message = api_upload_document(uploaded_file.name, file_bytes)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">📋 Your Uploaded Files</p>', unsafe_allow_html=True)
        docs = api_list_documents()
        if not docs:
            st.info("No documents uploaded yet.")
        else:
            search_query = st.text_input(
                "🔍 Search documents by name",
                value=st.session_state.doc_manager_prefill,
                placeholder="Type to filter list...",
            )
            st.session_state.doc_manager_prefill = ""
            sort_by = st.selectbox("Sort By", ["Upload Date (Newest)", "Name (A-Z)", "File Size (Largest)"])

            filtered_docs = docs
            if search_query:
                filtered_docs = [d for d in docs if search_query.lower() in d["filename"].lower()]

            if sort_by == "Upload Date (Newest)":
                filtered_docs.sort(key=lambda x: x["upload_date"], reverse=True)
            elif sort_by == "Name (A-Z)":
                filtered_docs.sort(key=lambda x: x["filename"].lower())
            elif sort_by == "File Size (Largest)":
                filtered_docs.sort(key=lambda x: x["size_bytes"], reverse=True)

            for doc in filtered_docs:
                doc_id = doc["id"]
                upload_time = datetime.datetime.fromisoformat(doc["upload_date"]).strftime("%Y-%m-%d %H:%M")
                status_ok = doc["embedding_status"] == "PROCESSED"

                c_info, c_prev, c_chat, c_del = st.columns([4, 1, 1, 1])
                with c_info:
                    st.markdown(
                        f"""
                        <div style="padding:6px 0;">
                            <span style="font-weight:600;font-size:14.5px;">📄 {doc['filename']}</span>
                            <div class="doc-meta">
                                {doc['file_type'].upper()} • {format_size(doc['size_bytes'])} • {doc['chunk_count']} chunks
                                • <span class="cog-badge {'badge-green' if status_ok else 'badge-red'}">{doc['embedding_status']}</span>
                            </div>
                            <div class="doc-meta">Uploaded: {upload_time}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c_prev:
                    with st.popover("👁️", use_container_width=True):
                        st.markdown(f"**{doc['filename']}**")
                        st.write(f"Type: {doc['file_type'].upper()}")
                        st.write(f"Size: {format_size(doc['size_bytes'])}")
                        st.write(f"Chunks: {doc['chunk_count']}")
                        st.write(f"Status: {doc['embedding_status']}")
                        st.write(f"Uploaded: {upload_time}")
                with c_chat:
                    if st.button("💬", key=f"chat_{doc_id}", use_container_width=True, help="Ask questions about this document"):
                        st.session_state.pending_chat_doc_id = doc_id
                        st.session_state.current_page = "Chat Arena"
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"del_{doc_id}", use_container_width=True, help="Delete document"):
                        with st.spinner("Deleting document and rebuilding index..."):
                            success, message = api_delete_document(doc_id)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                st.markdown('<hr style="margin:4px 0;border:0;border-top:1px solid var(--border);"/>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# CHAT ARENA
# ============================================================
def render_chat_arena():
    st.markdown('<h2 style="font-weight:800;">💬 Cognify QA Arena</h2>', unsafe_allow_html=True)

    docs = api_list_documents()
    doc_options = {"🌐 All Documents": None}
    for doc in docs:
        if doc["embedding_status"] == "PROCESSED":
            doc_options[f"📄 {doc['filename']} ({doc['file_type'].upper()})"] = doc["id"]

    default_index = 0
    if st.session_state.pending_chat_doc_id != "__unset__":
        for i, (label, doc_id) in enumerate(doc_options.items()):
            if doc_id == st.session_state.pending_chat_doc_id:
                default_index = i
                break
        st.session_state.pending_chat_doc_id = "__unset__"

    col_filter, col_clear = st.columns([4, 1])
    with col_filter:
        selected_doc_label = st.selectbox(
            "Filter Context by Document",
            list(doc_options.keys()),
            index=default_index,
            help="Select a specific document to narrow search context, or search all available.",
        )
        selected_doc_id = doc_options[selected_doc_label]
    with col_clear:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat", help="Clear current session chat history"):
            st.session_state.chat_history_state = []
            st.rerun()

    for idx, msg in enumerate(st.session_state.chat_history_state):
        is_user = msg["role"] == "user"
        role_label  = "👤 YOU"        if is_user else "🤖 COGNIFY DOCS AI"
        bubble_cls  = "user"          if is_user else "ai"
        meta_badge  = ""
        if not is_user and "response_time" in msg:
            meta_badge = f'<span class="chat-meta-badge">⚡ {msg["response_time"]:.1f}s</span>'

        # ── Render each bubble as a self-contained block ───────────────────
        # User bubbles: pure HTML (text is escaped — no tag leaking possible)
        if is_user:
            clean = _html.escape(msg["text"].strip())
            st.markdown(
                f'<div class="chat-row user">'
                f'<div class="chat-bubble user">'
                f'<div class="chat-role-label">{role_label}</div>'
                f'<div class="chat-text">{clean}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            # AI bubbles: header in HTML, then native st.markdown for content
            # (avoids Streamlit parser generating mismatched tags inside our HTML)
            st.markdown(
                f'<div class="chat-row ai">'
                f'<div class="chat-bubble ai">'
                f'<div class="chat-role-label">{role_label}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(msg["text"])          # native markdown — no unsafe_allow_html
            if meta_badge:
                st.markdown(meta_badge, unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

            # Copy button
            b64 = base64.b64encode(msg["text"].encode()).decode("ascii")
            st.markdown(
                f'<button class="copy-btn" onclick="navigator.clipboard.writeText(atob(\'{b64}\'))">📋 Copy</button>',
                unsafe_allow_html=True,
            )

            # Citations
            if msg.get("citations"):
                with st.expander("📚 Show retrieved sources"):
                    for cit in msg["citations"]:
                        page_info = f" | Page {cit['page_number']}" if cit.get("page_number") else ""
                        st.markdown(
                            f'<div class="citation-box">'
                            f'<b>📄 {_html.escape(str(cit["document_name"]))}</b>{page_info}'
                            f'<p style="margin-top:8px;font-style:italic;">'
                            f'"{_html.escape(str(cit["chunk_text"]))}"</p></div>',
                            unsafe_allow_html=True,
                        )

            # Regenerate button — only on last AI reply
            if idx == len(st.session_state.chat_history_state) - 1:
                prev = st.session_state.chat_history_state[idx - 1] if idx > 0 else None
                if prev and prev["role"] == "user":
                    if st.button("🔄 Regenerate response", key=f"regen_{idx}"):
                        with st.spinner("Regenerating…"):
                            start = time.perf_counter()
                            ok, payload = api_chat(prev["text"], selected_doc_id)
                            elapsed = time.perf_counter() - start
                            st.session_state.chat_history_state[idx] = {
                                "role": "ai", "text": payload["answer"],
                                "citations": payload.get("citations", []),
                                "response_time": elapsed,
                            }
                            st.rerun()

    with st.form("chat_input_form", clear_on_submit=True):
        user_query = st.text_input(
            "Ask a question based on your indexed documents",
            placeholder="E.g., What are the key findings in chapter 2?",
        )
        submit_chat = st.form_submit_button("🚀 Send Query")

        if submit_chat and user_query.strip() != "":
            st.session_state.chat_history_state.append({"role": "user", "text": user_query})
            with st.spinner("🔄 Retrieving local documents and generating answer..."):
                start = time.perf_counter()
                success, response_payload = api_chat(user_query, selected_doc_id)
                elapsed = time.perf_counter() - start
                st.session_state.chat_response_times.append(elapsed)
                st.session_state.chat_history_state.append({
                    "role": "ai",
                    "text": response_payload["answer"],
                    "citations": response_payload.get("citations", []),
                    "response_time": elapsed,
                })
                st.rerun()


# ============================================================
# HISTORY EXPLORER
# ============================================================
def render_history_explorer():
    st.markdown('<h2 style="font-weight:800;">🔎 History Explorer</h2>', unsafe_allow_html=True)
    st.markdown('<div class="cog-card">', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        keyword = st.text_input("🔍 Search past questions and answers", placeholder="Enter keywords...")
    with col2:
        docs = api_list_documents()
        doc_options = {"🌐 All Documents": None}
        for doc in docs:
            doc_options[doc["filename"]] = doc["id"]
        selected_doc = st.selectbox("📄 Filter History by Document", list(doc_options.keys()))
        selected_doc_id = doc_options[selected_doc]

    history = api_get_history(q=keyword, document_id=selected_doc_id)

    if not history:
        st.info("No matching conversations found.")
    else:
        if st.button("⬇️ Export History"):
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["timestamp", "document", "question", "answer"])
            for item in history:
                writer.writerow([
                    item["timestamp"],
                    item.get("document_name", "All Documents"),
                    item["question"],
                    item["answer"],
                ])
            st.download_button(
                "Download CSV",
                data=buf.getvalue(),
                file_name="cognify_history_export.csv",
                mime="text/csv",
            )

        st.markdown('<div class="timeline-wrap">', unsafe_allow_html=True)
        for item in history:
            timestamp_str = datetime.datetime.fromisoformat(item["timestamp"]).strftime("%b %d, %Y %H:%M:%S")
            doc_scope = f"📄 {item['document_name']}" if item.get("document_name") else "🌐 All Documents"
            st.markdown(
                f"""
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-muted);margin-bottom:6px;">
                        <span>🕐 {timestamp_str}</span>
                        <span class="cog-badge badge-purple">{doc_scope}</span>
                    </div>
                    <div style="margin-bottom:6px;"><b style="color:var(--accent);">❓ Q:</b> {item['question']}</div>
                    <div><b style="color:var(--secondary);">💡 A:</b> {item['answer']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# SETTINGS
# ============================================================
def render_settings():
    st.markdown('<h2 style="font-weight:800;">⚙️ Profile & Settings</h2>', unsafe_allow_html=True)

    success, profile_data = api_get_profile()
    if not success:
        st.error("Failed to load user profile statistics.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">👤 User Details</p>', unsafe_allow_html=True)
        reg_time = datetime.datetime.fromisoformat(profile_data["created_at"]).strftime("%b %d, %Y %H:%M")
        st.markdown(f"**👤 Username:** {profile_data['username']}")
        st.markdown(f"**📅 Member Since:** {reg_time}")
        st.markdown("**🗄️ Database Engine:** SQLite (Local)")
        st.markdown("**🔐 Authentication:** JWT (Stateful Sessions)")
        if st.button("🚪 Log Out"):
            api_logout()
            st.success("Successfully logged out.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">🎨 Theme</p>', unsafe_allow_html=True)
        theme_choice = st.radio(
            "Interface theme", ["dark", "light"],
            index=0 if st.session_state.theme == "dark" else 1,
            horizontal=True, label_visibility="collapsed",
        )
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">🧠 RAG Settings</p>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="line-height:2;font-size:13.5px;">
            - <b>Embedding Model:</b> <code>sentence-transformers/{os.environ.get('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')}</code>
            <br>- <b>Vector Store:</b> FAISS (CPU mode)
            <br>- <b>Text Chunk Size:</b> 1000 characters
            <br>- <b>Text Chunk Overlap:</b> 100 characters
            <br>- <b>Google LLM Engine:</b> <code>gemini-1.5-flash</code>
            <br>- <b>Target Device:</b> Local CPU Execution
            <br>- <b>Session Expiration:</b> 60 Minutes
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">⌨️ Keyboard Shortcuts</p>', unsafe_allow_html=True)
        st.markdown(
            """
            <div style="line-height:2;font-size:13.5px;">
            - <b>Ctrl + K</b> — Focus global search
            <br>- <b>Enter</b> — Submit chat query / search
            <br>- <b>Esc</b> — Close popovers / expanders
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="cog-card">', unsafe_allow_html=True)
        st.markdown('<p class="cog-card-title">ℹ️ About Cognify Docs</p>', unsafe_allow_html=True)
        st.markdown(
            """
            <div style="line-height:2;font-size:13.5px;">
            AI-Powered Local Document Chat System using Retrieval-Augmented Generation (RAG).
            Built with Streamlit, FastAPI, LangChain, FAISS, HuggingFace embeddings, Gemini and SQLite.
            <br><b>Version:</b> 1.0.0 &nbsp;|&nbsp; <b>Release:</b> July 2026
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# MAIN ROUTER
# ============================================================
def main():
    _inject_styles()

    if not st.session_state.logged_in:
        render_auth_page()
        return

    render_header()
    render_sidebar()

    page = st.session_state.current_page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Document Manager":
        render_doc_manager()
    elif page == "Chat Arena":
        render_chat_arena()
    elif page == "History Explorer":
        render_history_explorer()
    elif page == "Profile & Settings":
        render_settings()

    render_footer()


if __name__ == "__main__":
    main()
