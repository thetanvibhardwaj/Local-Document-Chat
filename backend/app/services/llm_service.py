"""
Thin wrapper module kept for architectural symmetry with the spec's
"LLM Service" backend module. The actual Gemini call lives in
app.rag.chains.rag_chain to keep the RAG pipeline cohesive in one place;
this module re-exports it under the expected service name.
"""
from app.rag.chains.rag_chain import RagAnswer, answer_question

__all__ = ["RagAnswer", "answer_question"]
