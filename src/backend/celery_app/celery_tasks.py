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
from backend.database.models import IndexingStatus
from backend.service.file_service import FileService
from RAG.chroma_db import create_vector_store
from RAG.document_indexing_seervice import DocumentIndexingService
from RAG.file_vector_repository import FileVectorStorage


class FileTask(Task):
    """Custom Celery task base class for managing file indexing lifecycle.

    Provides a cached SQLAlchemy session factory and updates file indexing
    status in the application database before task execution.

    Database resources are initialized lazily and reused across tasks
    within the same worker process.
    """

    _session_factory = None
    _engine = None
    settings = get_settings()
    set_up_logging()

    @classmethod
    def create_session_factory(cls) -> sessionmaker:
        """Create and cache a SQLAlchemy session factory for Celery tasks.

        Lazily initializes the database engine and session factory on the
        first invocation. Subsequent calls reuse the cached resources.

        Returns:
            sessionmaker: SQLAlchemy session factory bound to the database engine.
        """
        if cls._engine is None:
            cls._engine = get_engine(DB_URL=cls.settings.db_url)
            cls._session_factory = session_factory(cls._engine)
        return cls._session_factory  # type: ignore

    def before_start(self, task_id, args, kwargs):
        """Update file indexing status before Celery task execution.

        Called by Celery immediately before the task starts executing.
        Extracts the user and file identifiers from task keyword arguments,
        creates a database session, and marks the file indexing status
        as PENDING.

        Database update failures are logged without interrupting task execution.

        Args:
            task_id (str): Unique identifier of the Celery task.
            args (tuple): Positional arguments passed to the task.
            kwargs (dict): Keyword arguments containing user_id and file_id.

        Returns:
            None.
        """
        with logger.contextualize(request_id=task_id):
            logger.debug(f"Celery picekd up the task {task_id}")
            user_id: int = kwargs.get("user_id")
            file_id: int = kwargs.get("file_id")
            try:
                session_factory = self.create_session_factory()

                with session_factory() as session:  # session context menager

                    file_repo = FileRepository(db_session=session)
                    file_service = FileService(file_repository=file_repo)

                    file_service.update_idnexing_status(
                        user_id=user_id,
                        file_id=file_id,
                        new_status=IndexingStatus.PROCESSING,
                    )
                    logger.debug(f"Successfully saved task {task_id} as PENDING to DB")
            except Exception:
                logger.exception(
                    f"Issue occured while saving task {task_id} of Indexing in Celery to DB"
                )

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
    file_id: int,
    request_id: str | None = None,
):
    """Index an uploaded document and store its chunks in the vector database.

    Runs as a bound Celery task using the custom FileTask base class.
    Loads and splits the uploaded document, generates embeddings, and
    stores the resulting chunks in the vector database.

    Automatically retries up to three times on ConnectionError or
    TimeoutError with exponential backoff. FileNotFoundError does not
    trigger an automatic retry.

    Args:
        self: Bound Celery task instance.
        file_path (str): Path to the uploaded document.
        user_id (int): ID of the user who owns the document.
        file_id (int): ID of the file record in the application database.
        request_id (str | None): Optional request identifier used for
            log correlation.

    Returns:
        None: The task stores document embeddings without returning a result.
    """

    with logger.contextualize(request_id=request_id):
        logger.debug("Starting document indexing in Celery")

        service = get_vector_store_service()

        service.add_document(
            file_path=Path(file_path), user_id=user_id, file_db_id=file_id
        )

        logger.debug("Document indexing completed in Celery")
