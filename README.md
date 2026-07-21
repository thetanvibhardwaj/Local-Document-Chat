# AI-Powered Local Document Chat System (RAG)

## Overview

The **AI-Powered Local Document Chat System** is a Retrieval-Augmented Generation (RAG) application that enables users to upload documents and interact with them using natural language. Instead of manually searching through multiple files, users can ask questions, and the system retrieves the most relevant information from the uploaded documents before generating an accurate response using Google's Gemini LLM.

## Problem Statement

Organizations store a large number of documents such as HR policies, technical manuals, contracts, reports, and training materials. Searching for specific information manually is time-consuming and inefficient. This project provides an intelligent document assistant that understands document content and delivers context-aware answers, improving productivity and reducing search time.

## Tech Stack

* **Backend:** Python, FastAPI
* **Frontend:** Streamlit (Future scope: React)
* **LLM:** Google Gemini
* **Framework:** LangChain
* **Embeddings:** Gemini Embeddings
* **Chunking:** LangChain Recursive Character Text Splitter
* **Vector Database:** Neon PostgreSQL with pgvector
* **Database:** PostgreSQL (User Authentication & Chat History)

## System Workflow

1. User registers and logs into the application.
2. Documents (PDF, DOCX, TXT) are uploaded through the Python backend.
3. The uploaded documents are processed and divided into smaller chunks using LangChain.
4. Gemini Embeddings are generated for each chunk and stored in **Neon PostgreSQL (pgvector)**.
5. When a user asks a question, the system retrieves the most relevant document chunks using semantic similarity search.
6. The retrieved context is sent to the Gemini LLM to generate an accurate, context-aware response.
7. Chat history and user information are stored in PostgreSQL for future reference.

## Key Features

* Secure user authentication
* Upload multiple documents
* Intelligent document chunking
* Semantic search using embeddings
* Context-aware AI responses
* Chat history management
* Scalable RAG architecture
* Modular backend for future enhancements

## Future Enhancements

* React-based frontend
* OCR support for scanned documents
* Multi-language support
* Voice-based interaction
* Document summarization
* Admin dashboard and analytics

## Conclusion

The AI-Powered Local Document Chat System leverages modern RAG architecture, LangChain, Gemini LLM, and vector search to provide fast, accurate, and intelligent document querying. The system is designed with a modular and scalable architecture, making it suitable for both academic projects and enterprise-level knowledge management applications.
