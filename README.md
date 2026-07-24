## System Architecture

The following architecture diagram illustrates the overall design and workflow of **Cognify Docs**, an AI-Powered Document Management and Intelligent Chat Assistant. It demonstrates how the frontend, backend, database, and AI components interact to provide secure document management and context-aware question answering.

### Architecture Overview

The application follows a modular architecture consisting of the following layers:

- **Frontend:** Developed using Streamlit with custom HTML and CSS to provide an intuitive interface for user authentication, dashboard, document management, AI chat, analytics, and settings.
- **Backend:** Built with FastAPI to handle authentication, document processing, API requests, and communication between the frontend and AI components.
- **Database:** SQLite is used to securely store user information, document metadata, and chat history.
- **AI/RAG Pipeline:** Uploaded documents are processed, converted into vector embeddings using Sentence Transformers, indexed in FAISS, and queried through the Google Gemini API to generate context-aware responses.
- **Vector Store:** FAISS performs semantic similarity search to retrieve the most relevant document content before answer generation.

### System Workflow

1. The user logs into the application.
2. Documents are uploaded through the frontend interface.
3. The backend processes the uploaded documents and stores metadata in the SQLite database.
4. Document text is extracted, divided into smaller chunks, converted into embeddings, and indexed in the FAISS vector database.
5. When a user submits a question, the system converts the query into an embedding and performs a semantic search in FAISS.
6. The retrieved document context is provided to the Google Gemini API to generate an accurate response.
7. The generated response is displayed to the user through the AI Chat interface.

### System Architecture Diagram

**Figure 1:** High-level architecture of Cognify Docs illustrating the interaction between the Streamlit frontend, FastAPI backend, SQLite database, AI/RAG pipeline, and FAISS vector store.
