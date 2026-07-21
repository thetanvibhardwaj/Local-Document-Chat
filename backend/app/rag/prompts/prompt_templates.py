"""
Prompt templates enforcing strict grounded-answer behaviour.
The system prompt explicitly forbids fabrication and mandates the
fallback message when context is insufficient, per the project spec.
"""
from langchain_core.prompts import ChatPromptTemplate

NO_CONTEXT_FALLBACK = "I couldn't find relevant information in the uploaded documents."
INSUFFICIENT_CONTEXT_FALLBACK = "I don't have enough information from the uploaded documents."

SYSTEM_PROMPT = """You are DocuChat AI, an enterprise document assistant.

STRICT RULES:
1. Answer ONLY using the provided CONTEXT below. Never use outside knowledge.
2. If the context does not contain enough information to answer confidently, reply
   EXACTLY with: "{insufficient_context}"
3. Never invent facts, numbers, names, or policies that are not present in the context.
4. When you use information from the context, mention which document(s) it came from
   (the document names are provided alongside each context chunk).
5. If multiple documents contain relevant information, synthesize them into one
   coherent answer and cite all documents used.
6. Be concise, professional, and directly answer the question asked.

CONTEXT:
{context}
"""

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)


def format_context(chunks: list) -> str:
    """
    Format retrieved chunks into a single context string, each chunk tagged
    with its source document name so the LLM can cite it correctly.
    """
    if not chunks:
        return ""
    blocks = []
    for c in chunks:
        blocks.append(f"[Source: {c.filename} | chunk #{c.chunk_number}]\n{c.chunk_text}")
    return "\n\n---\n\n".join(blocks)
