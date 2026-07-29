import time
import random
from typing import Dict, List, Any, Optional
from google import genai
from backend.utils.config import settings
from backend.utils.logger import logger
from backend.rag.vector_store import VectorStoreManager

PROMPT_TEMPLATE = """You are Cognify Docs AI, a precise document Q&A assistant.
Analyze the provided context chunks below and answer the user's question.

CRITICAL INSTRUCTIONS:
1. Answer ONLY based on the provided context.
2. If the context does not contain the answer, respond EXACTLY: "I couldn't find relevant information in the uploaded documents."
3. Do not hallucinate or use external knowledge.
4. Keep the answer concise and factual.

Context Chunks:
{context}

Question: {question}

Answer:"""

# ── Models ordered by confirmed availability for this API key ─────────────────
# Based on live testing: gemini-3.5-flash-lite is confirmed working FIRST.
# 404 models (gemini-2.5-flash, gemini-2.5-flash-lite) removed entirely.
_MODEL_PRIORITY = [
    "models/gemini-3.5-flash-lite",   # ✓ CONFIRMED working — try first for speed
    "models/gemini-3.5-flash",         # sometimes 503 but available
    "models/gemini-3.1-flash-lite",    # lightweight fallback
    "models/gemini-2.0-flash-lite",    # 429 quota but worth a try
    "models/gemini-2.0-flash",         # 429 quota last resort
]

_MAX_RETRIES = 3     # retries per model
_BASE_DELAY  = 1.0   # seconds
_MAX_DELAY   = 6.0


def _try_model(client: genai.Client, model: str, prompt: str) -> str:
    """
    Calls a single Gemini model with exponential back-off on 503/429.
    Returns answer text on success, raises on permanent failure.
    """
    delay = _BASE_DELAY
    last_exc = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            return "I couldn't find relevant information in the uploaded documents."

        except Exception as e:
            err_str = str(e)
            is_retryable = any(x in err_str for x in [
                "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                "quota", "rate", "overload"
            ])
            last_exc = e

            if is_retryable and attempt < _MAX_RETRIES:
                jitter = random.uniform(0, 0.4 * delay)
                sleep_for = min(delay + jitter, _MAX_DELAY)
                logger.warning(
                    f"[RETRY {attempt}/{_MAX_RETRIES}] Model '{model}' transient error "
                    f"({type(e).__name__}). Sleeping {sleep_for:.1f}s…"
                )
                time.sleep(sleep_for)
                delay = min(delay * 2, _MAX_DELAY)
            else:
                # Non-retryable OR final attempt — bubble up to try next model
                raise

    raise last_exc


class RAGService:
    @staticmethod
    def query_rag(user_id: int, question: str, document_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Full RAG pipeline with multi-model fallback and retry on 503/429.
        """
        fallback_response = {
            "answer": "I couldn't find relevant information in the uploaded documents.",
            "citations": []
        }

        # 1. API key check
        if not settings.gemini_api_key or settings.gemini_api_key.strip() == "":
            logger.error("GEMINI_API_KEY is not configured.")
            return {
                "answer": "Error: Gemini API Key is not set in the .env file.",
                "citations": []
            }

        # 2. Get FAISS retriever
        retriever = VectorStoreManager.get_retriever(
            user_id=user_id, document_id=document_id, k=4
        )
        if retriever is None:
            logger.warning(f"No FAISS index for user {user_id}.")
            return fallback_response

        # 3. Semantic search
        try:
            relevant_docs = retriever.invoke(question)
        except Exception as e:
            logger.error(f"FAISS retrieval error: {e}", exc_info=True)
            return fallback_response

        if not relevant_docs:
            return fallback_response

        # 4. Build context
        context_blocks = []
        for idx, doc in enumerate(relevant_docs):
            fname = doc.metadata.get("filename", "Unknown")
            page  = doc.metadata.get("page", "N/A")
            context_blocks.append(
                f"--- Chunk {idx+1} | {fname} | Page {page} ---\n{doc.page_content}"
            )
        context_string = "\n\n".join(context_blocks)

        # 5. Format prompt
        prompt_text = PROMPT_TEMPLATE.format(
            context=context_string, question=question
        )

        # 6. Try each model in priority order
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options={"timeout": 60000}
        )
        answer = None

        for model in _MODEL_PRIORITY:
            try:
                logger.info(f"[RAG] Trying model '{model}' for user_{user_id}…")
                answer = _try_model(client, model, prompt_text)
                logger.info(f"[RAG] ✓ Success with '{model}'")
                break
            except Exception as e:
                logger.warning(f"[RAG] ✗ Model '{model}' failed: {type(e).__name__}: {str(e)[:120]}. Trying next…")
                continue

        if answer is None:
            return {
                "answer": (
                    "⚠️ All Gemini models are temporarily overloaded (API rate limit). "
                    "Please wait 10–15 seconds and try again. "
                    "This is a Google API quota issue, not a bug in the system."
                ),
                "citations": []
            }

        # 7. Check for fallback indicator
        if "I couldn't find relevant information" in answer:
            return fallback_response

        # 8. Build citations
        citations = [
            {
                "document_name": doc.metadata.get("filename", "Unknown"),
                "page_number":   doc.metadata.get("page"),
                "chunk_text":    doc.page_content,
            }
            for doc in relevant_docs
        ]

        logger.info(f"[RAG] Answer ready for user_{user_id} ({len(citations)} citations)")
        return {"answer": answer, "citations": citations}
