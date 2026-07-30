import os
import shutil
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from backend.utils.config import settings
from backend.utils.logger import logger


class VectorStoreManager:
    _embeddings = None

    @classmethod
    def get_embeddings(cls) -> HuggingFaceEmbeddings:
        """
        Lazy load embedding model so it only loads when needed.
        """
        if cls._embeddings is None:
            # Safeguard stream flush methods to prevent tqdm/transformers from crashing with [Errno 22]
            try:
                import sys
                for stream in (sys.stdout, sys.stderr):
                    if hasattr(stream, "flush"):
                        original_flush = stream.flush
                        def make_safe_flush(orig_flush):
                            def safe_flush():
                                try:
                                    orig_flush()
                                except OSError as e:
                                    if e.errno == 22:
                                        pass  # Ignore Errno 22 (Invalid argument)
                                    else:
                                        raise
                            return safe_flush
                        stream.flush = make_safe_flush(original_flush)
            except Exception:
                pass

            # Force disable tqdm progress bars
            try:
                import tqdm
                if not hasattr(tqdm, "_original_init"):
                    tqdm._original_init = tqdm.tqdm.__init__
                tqdm.tqdm.__init__ = lambda self, *args, **kwargs: tqdm._original_init(self, *args, **{**kwargs, "disable": True})
            except Exception:
                pass

            # Disable transformers progress bars
            try:
                from transformers.utils.logging import disable_progress_bar
                disable_progress_bar()
            except Exception:
                pass

            # Force entire HuggingFace stack to work offline (model is already cached locally)
            # This prevents httpx "client has been closed" errors under Uvicorn's StatReload
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

            logger.info(f"Loading embedding model: {settings.embedding_model_name}")
            try:
                cls._embeddings = HuggingFaceEmbeddings(
                    model_name=settings.embedding_model_name,
                    model_kwargs={"device": "cpu", "local_files_only": True}
                )
                logger.info("Embedding model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}", exc_info=True)
                raise

        return cls._embeddings

    @staticmethod
    def get_user_index_path(user_id: int) -> str:
        path = os.path.abspath(
            os.path.join(settings.vector_store_dir, f"user_{user_id}")
        )
        return path

    @classmethod
    def index_exists(cls, user_id: int) -> bool:
        path = cls.get_user_index_path(user_id)

        exists = os.path.exists(os.path.join(path, "index.faiss"))

        logger.info(f"[INDEX_EXISTS]")
        logger.info(f"Path   : {path}")
        logger.info(f"Exists : {exists}")

        return exists

    @classmethod
    def save_or_update_index(cls, user_id: int, chunks: List[Document]) -> None:

        if not chunks:
            logger.warning("No chunks received. Nothing to index.")
            return

        embeddings = cls.get_embeddings()
        path = cls.get_user_index_path(user_id)

        logger.info("======================================================")
        logger.info("STARTING FAISS SAVE")
        logger.info(f"User ID          : {user_id}")
        logger.info(f"Chunks           : {len(chunks)}")
        logger.info(f"Vector Root      : {settings.vector_store_dir}")
        logger.info(f"Absolute Path    : {path}")
        logger.info(f"Path Exists      : {os.path.exists(path)}")
        logger.info("======================================================")

        try:

            if cls.index_exists(user_id):

                logger.info("Loading existing FAISS index...")

                db = FAISS.load_local(
                    path,
                    embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("Sample metadata:")
                for i in range(min(5, len(db.docstore._dict))):
                    key = list(db.docstore._dict.keys())[i]
                    doc = db.docstore._dict[key]
                    logger.info(doc.metadata)

                db.add_documents(chunks)

                logger.info(f"Added {len(chunks)} chunks.")

            else:

                logger.info("Creating NEW FAISS index...")

                db = FAISS.from_documents(chunks, embeddings)

            os.makedirs(path, exist_ok=True)

            logger.info("Saving FAISS index to disk...")

            db.save_local(path)

            logger.info("SAVE COMPLETE")

            logger.info(f"Directory Exists : {os.path.exists(path)}")
            logger.info(
                f"index.faiss      : {os.path.exists(os.path.join(path,'index.faiss'))}"
            )
            logger.info(
                f"index.pkl        : {os.path.exists(os.path.join(path,'index.pkl'))}"
            )

            if os.path.exists(path):
                logger.info(f"Directory Contents : {os.listdir(path)}")

            logger.info("======================================================")

        except Exception as e:
            logger.error("FAISS SAVE FAILED", exc_info=True)
            raise RuntimeError(str(e))

    @classmethod
    def rebuild_index(cls, user_id: int, all_user_chunks: List[Document]) -> None:

        path = cls.get_user_index_path(user_id)

        if not all_user_chunks:

            if os.path.exists(path):
                shutil.rmtree(path)
                logger.info(f"Deleted FAISS directory: {path}")

            return

        embeddings = cls.get_embeddings()

        try:

            logger.info(f"Rebuilding FAISS index at {path}")

            db = FAISS.from_documents(all_user_chunks, embeddings)

            os.makedirs(path, exist_ok=True)

            db.save_local(path)

            logger.info("Rebuild complete.")

        except Exception as e:
            logger.error(f"FAISS rebuild failed: {e}", exc_info=True)
            raise RuntimeError(str(e))

    @classmethod
    def get_retriever(
        cls,
        user_id: int,
        document_id: Optional[int] = None,
        k: int = 4
    ):

        if not cls.index_exists(user_id):
            logger.warning("Retriever requested but index does not exist.")
            return None

        embeddings = cls.get_embeddings()

        path = cls.get_user_index_path(user_id)

        logger.info("=" * 60)
        logger.info("LOADING FAISS")
        logger.info(f"Path : {path}")
        logger.info("=" * 60)

        try:

            db = FAISS.load_local(
                path,
                embeddings,
                allow_dangerous_deserialization=True
            )

            logger.info(f"Total vectors in index : {db.index.ntotal}")

            if document_id is not None:
                logger.info(f"Filtering document_id : {document_id}")
            else:
                logger.info("No document filter applied")

            search_kwargs = {
                "k": k
            }

        # Apply filter ONLY if metadata actually exists
            if document_id is not None:
                search_kwargs["filter"] = lambda metadata: (
                    metadata.get("document_id") == document_id
                )

            retriever = db.as_retriever(
                search_kwargs=search_kwargs
            )

            logger.info(f"Retriever kwargs : {search_kwargs}")

            return retriever

        except Exception as e:
            logger.error(f"Retriever load failed: {e}", exc_info=True)
            return None