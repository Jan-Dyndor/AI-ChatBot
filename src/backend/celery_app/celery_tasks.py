from functools import lru_cache
from pathlib import Path

from celery import Task
from loguru import logger
from sqlalchemy.orm import sessionmaker

from backend.celery_app.celery_app import celery_app
from backend.configuration.logging_config import set_up_logging
from backend.configuration.settings import get_settings
from backend.database.db import get_engine, session_factory
from backend.database.file_repository import FileRepository
from backend.service.file_service import FileService
from RAG.chroma_db import create_vector_store
from RAG.document_indexing_seervice import DocumentIndexingService
from RAG.file_vector_repository import FileVectorStorage


class FileTask(Task):
    _session_factory = None
    _engine = None
    settings = get_settings()
    set_up_logging()

    @classmethod
    def create_session_factory(cls) -> sessionmaker:
        """Create and cache the SQLAlchemy session factory for Celery tasks.

        Returns:
            Session factory bound to the application's database engine.
        """
        if cls._engine is None:
            cls._engine = get_engine(DB_URL=cls.settings.db_url)
            cls._session_factory = session_factory(cls._engine)
        return cls._session_factory  # type: ignore

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Persist the final Celery task status in the related file record.

        Args:
            status: Final Celery task state, such as ``SUCCESS`` or ``FAILURE``.
            retval: Task return value or raised exception.
            task_id: Unique ID of the completed task.
            args: Positional arguments passed to the task.
            kwargs: Keyword arguments passed to the task; must include ``user_id``
                and ``file_id``.
            einfo: Exception information when the task fails.
        """
        with logger.contextualize(request_id=task_id):
            logger.debug(f"Saving task {task_id} progress to DB")
            user_id: int = kwargs.get("user_id")
            file_id: int = kwargs.get("file_id")
            session_factory = self.create_session_factory()

            with session_factory() as session:  # session context menager

                file_repo = FileRepository(db_session=session)
                file_service = FileService(file_repository=file_repo)

                file_service.update_idnexing_status(
                    user_id=user_id, file_id=file_id, new_status=status
                )
                logger.debug(f"Successfully saved task {task_id} progress to DB")


@lru_cache(maxsize=1)
def get_vector_store_service() -> FileVectorStorage:
    """Create and cache the service used to index and store uploaded documents.

    The service is initialized once per worker process with vector-store and
    document-chunking settings from the application configuration.

    Returns:
        Configured file vector storage service.
    """
    set_up_logging()
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


@celery_app.task(
    name="index_upload_file",
    base=FileTask,
    bind=True,
    max_retries=3,
    retry_backoff=True,
    autoretry_for=(ConnectionError, TimeoutError),
    dont_autoretry_for=(FileNotFoundError,),
)
def index_and_save_file(
    self,
    file_path: str,
    user_id: int,
    request_id: str | None = None,
    file_id: int | None = None,
):
    """Index an uploaded document and store its contents in the vector database.

    Args:
        self: Bound Celery task instance.
        file_path: Absolute path to the uploaded file.
        user_id: ID of the user who uploaded the file.
        request_id: Identifier used to correlate logs and the Celery task.
        file_id: ID of the file record in the application database.
    """

    with logger.contextualize(request_id=request_id):
        logger.debug("Starting document indexing in Celery")

        service = get_vector_store_service()

        service.add_document(
            file_path=Path(file_path),
            user_id=user_id,
        )

        logger.debug("Document indexing completed in Celery")
