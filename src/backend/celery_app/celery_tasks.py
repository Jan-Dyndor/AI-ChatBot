from functools import lru_cache
from pathlib import Path

from loguru import logger

from backend.celery_app.celery import celery_app
from backend.configuration.settings import get_settings
from RAG.chroma_db import create_vector_store
from RAG.document_indexing_seervice import DocumentIndexingService
from RAG.file_vector_repository import FileVectorStorage


@lru_cache(maxsize=1)
def get_vector_store_service() -> FileVectorStorage:
    settings = get_settings()

    vector_store = create_vector_store(
        embedding_model=settings.embedding_model,
        collection_name=settings.collection_name_vector_store,
        ollama_url=settings.ollama_url,
        host=settings.chroma_db_host,
        port=settings.chroma_db_port,
    )

    document_index_service = DocumentIndexingService(
        chunk_overlap=settings.chunk_overlap,
        chunk_size=settings.chunk_size,
    )

    return FileVectorStorage(
        vector_db=vector_store,
        file_index_service=document_index_service,
    )


@celery_app.task(name="index_upload_file")
def index_and_save_file(file_path: str, user_id: int):
    logger.info("Starting document indexing in Celery")

    service = get_vector_store_service()

    service.add_document(
        file_path=Path(file_path),
        user_id=user_id,
    )

    logger.info("Document indexing completed in Celery")
