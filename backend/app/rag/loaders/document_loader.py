"""
Document loaders for supported file types.
Each loader extracts raw text from a file on disk. LangChain's community
loaders are used under the hood, wrapped so the rest of the app depends on
a single, stable interface: `load_document(path, file_type) -> str`.
"""
from pathlib import Path

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)

SUPPORTED_TYPES = {"pdf", "docx", "txt", "md"}


class UnsupportedFileTypeError(Exception):
    pass


def load_document(file_path: str, file_type: str) -> str:
    """
    Load a document from disk and return its full raw text.
    Raises UnsupportedFileTypeError for anything outside SUPPORTED_TYPES.
    """
    file_type = file_type.lower().lstrip(".")
    if file_type not in SUPPORTED_TYPES:
        raise UnsupportedFileTypeError(f"Unsupported file type: {file_type}")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_type == "pdf":
        loader = PyPDFLoader(str(path))
    elif file_type == "docx":
        loader = Docx2txtLoader(str(path))
    elif file_type == "md":
        loader = UnstructuredMarkdownLoader(str(path))
    else:  # txt
        loader = TextLoader(str(path), encoding="utf-8")

    pages = loader.load()
    return "\n\n".join(page.page_content for page in pages if page.page_content)
