import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader, CSVLoader
from backend.utils.logger import logger

class DocumentLoader:
    @staticmethod
    def load(file_path: str) -> List[Document]:
        """
        Loads document contents based on the file extension.
        Supports PDF, DOCX, TXT, and CSV formats.
        """
        if not os.path.exists(file_path):
            logger.error(f"Loader failed: File does not exist at '{file_path}'")
            raise FileNotFoundError(f"File not found at '{file_path}'")
            
        ext = os.path.splitext(file_path)[1].lower()
        logger.info(f"Initiating document loading for '{file_path}' using extension '{ext}'")
        
        try:
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                logger.info(f"Successfully loaded {len(docs)} pages from PDF '{file_path}'")
                return docs
            elif ext == ".docx":
                loader = Docx2txtLoader(file_path)
                docs = loader.load()
                logger.info(f"Successfully loaded DOCX document '{file_path}'")
                return docs
            elif ext == ".txt":
                # Use TextLoader specifying UTF-8 to prevent Windows local encoding issues
                loader = TextLoader(file_path, encoding="utf-8")
                docs = loader.load()
                logger.info(f"Successfully loaded TXT document '{file_path}'")
                return docs
            elif ext == ".csv":
                loader = CSVLoader(file_path, encoding="utf-8")
                docs = loader.load()
                logger.info(f"Successfully loaded {len(docs)} rows from CSV '{file_path}'")
                return docs
            else:
                logger.warning(f"Rejected loader call for unsupported file type: '{ext}'")
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            logger.error(f"Critical error during loading file '{file_path}': {e}", exc_info=True)
            raise RuntimeError(f"Document loading failed: {str(e)}")
