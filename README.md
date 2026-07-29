# 🚀 Cognify Docs: Enterprise RAG Knowledge Platform

An enterprise-grade, local Retrieval-Augmented Generation (RAG) Document Intelligence platform. It allows users to upload local files (PDFs, text, CSVs), automatically chunks and embeds them locally, and provides secure chat queries using Google Gemini models with intelligent multi-model fallbacks.

---

## 🌟 Key Features

- **Double-Layered Security**: Stateful JWT authentication coupled with local-first file processing.
- **Enterprise Visual Experience**: Stunning dark-themed Glassmorphism styling with customized Three.js interactive 3D visualizations.
- **Dynamic 3D Login Backdrop**: Built-in interactive particle system, knowledge graph, and simulated real-time data flow.
- **Intelligent RAG Pipeline**:
  - Auto-extracts chunks and creates vectors using `all-MiniLM-L6-v2`.
  - Local vector management via **FAISS** with document-level filtering.
- **High-Availability LLM Fallbacks**:
  - Implements a resilient 5-model retry chain (`gemini-3.5-flash-lite` ➔ `gemini-3.5-flash` ➔ `gemini-3.1-flash-lite` ➔ fallbacks).
  - Handles rate limits (`429`) and server load (`503`) seamlessly under high pressure.
- **Responsive Layout**: Designed for seamless viewport scaling across all screen sizes.

---

## 🛠️ Tech Stack

- **Frontend**: Streamlit, HTML5, Custom HSL Vanilla CSS, Three.js
- **Backend Services**: FastAPI, Uvicorn, LangChain, FAISS
- **Database**: SQLite (SQLAlchemy ORM)
- **Embedding & LLM**: HuggingFace SentenceTransformers, Google Gemini API

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10 or higher
- A valid Google Gemini API Key

### 2. Clone and Setup Environment
```bash
git clone https://github.com/your-username/cognify-docs.git
cd cognify-docs

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
