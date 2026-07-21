"""
Assembles the end-to-end RAG chain: retrieve -> prompt -> Gemini LLM -> parse.
This is the module the ChatService calls; it has no knowledge of FastAPI,
HTTP, or the database session lifecycle beyond what's passed in.
"""
import uuid
from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session

from app.config import settings
from app.rag.prompts import INSUFFICIENT_CONTEXT_FALLBACK, NO_CONTEXT_FALLBACK, RAG_PROMPT, format_context
from app.rag.retriever import RetrievedChunk, retrieve_relevant_chunks


@dataclass
class RagAnswer:
    answer: str
    sources: list[RetrievedChunk]


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.1,  # low temperature to minimize hallucination
    )


def answer_question(
    db: Session,
    user_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
) -> RagAnswer:
    """
    Run the full RAG pipeline for a single question:
    retrieve top-K chunks -> build grounded prompt -> call Gemini -> return answer + sources.
    """
    retrieved_chunks = retrieve_relevant_chunks(
        db=db, user_id=user_id, question=question, document_id=document_id
    )

    if not retrieved_chunks:
        return RagAnswer(answer=NO_CONTEXT_FALLBACK, sources=[])

    context = format_context(retrieved_chunks)
    chain = RAG_PROMPT | _get_llm() | StrOutputParser()

    answer_text = chain.invoke(
        {
            "context": context,
            "question": question,
            "insufficient_context": INSUFFICIENT_CONTEXT_FALLBACK,
        }
    )

    return RagAnswer(answer=answer_text.strip(), sources=retrieved_chunks)
