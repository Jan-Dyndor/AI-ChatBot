from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from loguru import logger
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from backend.exceptions.exc import ChromaDBError
from backend.retry.retry_logs_logic import (
    cleanup_and_log_final_retry_failure,
    log_retry_and_cleanup,
)
from RAG.document_indexing_seervice import DocumentIndexingService


class FileVectorStorage:
    def __init__(
        self, vector_db: VectorStore, file_index_service: DocumentIndexingService
    ) -> None:
        self.vector_storage = vector_db
        self.index_service = file_index_service

    @retry(
        stop=stop_after_attempt(3),
        reraise=True,
        wait=wait_exponential_jitter(initial=1, max=5, jitter=1),
        before_sleep=log_retry_and_cleanup,
        retry_error_callback=cleanup_and_log_final_retry_failure,
        retry=retry_if_not_exception_type(FileNotFoundError),
    )
    def add_document(self, file_path: Path, user_id: int, file_db_id: int):

        logger.info("Started DOC chunking and embedding process")

        doc_chunks, ids = self.index_service.load_and_split_pdf(
            file_path=file_path, user_id=user_id, file_db_id=file_db_id
        )

        self.vector_storage.add_documents(documents=doc_chunks, ids=ids)
        logger.info("Added Doc to Vector Store")

    def return_retiver(self, serach_kwargs: dict):
        retriver = self.vector_storage.as_retriever(
            search_type="similarity",
            search_kwargs=serach_kwargs,
        )

        return retriver

    def format_found_docs(self, docs):
        return "\n\n".join([doc.page_content for doc in docs])

    def delete_document(self, user_id: int, file_id: int):
        """Delete all vector database chunks belonging to a specific user document.

        Retrieves chunk identifiers from ChromaDB using user_id and file_id
        metadata filters, then deletes all matching chunks from the vector store.

        If no matching chunks are found, logs the result and returns without
        performing a deletion.

        Args:
            user_id (int): ID of the user who owns the document.
            file_id (int): ID of the file record in the application database.

        Returns:
            None: Matching document chunks are deleted from the vector database.
        """
        logger.info(
            f"Started deleting user {user_id} file {file_id} chunks from Vector Storage."
        )
        try:
            result = self.vector_storage.get(  # type: ignore
                where={
                    "$and": [
                        {"user_id": user_id},
                        {"file_id": file_id},
                    ]
                },
                include=[],
            )
            chunk_ids = result["ids"]

            if not chunk_ids:
                logger.info(
                    f"User's {user_id} has not chunks in Chroma for file {file_id}"
                )
                return

            self.vector_storage.delete(ids=chunk_ids)
            logger.info(
                f"Successuflly deleted user {user_id} file {file_id} chunks from Vector Storage."
            )
        except Exception as err:
            raise ChromaDBError(user_id=user_id, file_id=file_id) from err
