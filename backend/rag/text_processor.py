import re
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from backend.utils.logger import logger

class TextProcessor:
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Performs basic text cleanup (merges redundant spaces, normalizes 
        excessive newlines, strips edge whitespace).
        """
        if not text:
            return ""
        # Collapse multiple spaces and tabs to a single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Collapse three or more consecutive newlines to two
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def split_documents(
        documents: List[Document], 
        chunk_size: int = 1000, 
        chunk_overlap: int = 100
    ) -> List[Document]:
        """
        Cleans and splits raw text documents into smaller chunks using 
        LangChain's RecursiveCharacterTextSplitter.
        """
        cleaned_docs = []
        for idx, doc in enumerate(documents):
            cleaned_content = TextProcessor.clean_text(doc.page_content)
            if cleaned_content:
                # Standardize page metadata reference if missing
                metadata = doc.metadata.copy() if doc.metadata else {}
                if "page" not in metadata:
                    # Fallback to 1-indexed numbering or sheet tracking
                    metadata["page"] = metadata.get("page_number", idx + 1)
                
                cleaned_docs.append(Document(page_content=cleaned_content, metadata=metadata))
        
        # Initialize LangChain's recursive splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = splitter.split_documents(cleaned_docs)
        logger.info(f"Text processing complete: Split {len(documents)} pages into {len(chunks)} chunks.")
        return chunks
