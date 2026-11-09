from loguru import logger


def log_retry(retry_state):
    """Log a warning after a failed retry attempt.

    Extracts the attempt number and exception from the Tenacity
    retry state without interrupting the retry process.

    Args:
        retry_state (RetryCallState): Tenacity retry state containing
            the attempt number and the exception that caused the failure.
    """
    logger.warning(
        f"Retry attempt {retry_state.attempt_number} failed. "
        f"Error: {retry_state.outcome.exception()}"
    )


#! CHROMA DB


def log_retry_and_cleanup(retry_state):
    """Log a failed retry attempt and clean up document chunks from ChromaDB.

    Extracts the user and file identifiers from the retry state and
    attempts to delete the associated document chunks from the vector
    database before the next retry.

    Cleanup failures are logged without propagating the exception,
    allowing the retry process to continue.

    Args:
        retry_state (RetryCallState): Tenacity retry state containing
            the failed attempt details, instance reference, and
            document identifiers.
    """

    logger.warning(
        f"Retry attempt {retry_state.attempt_number} failed. Processing with ChromaDB file cleanup "
        f"Error: {retry_state.outcome.exception()}"
    )
    class_instance = retry_state.args[0]
    user_id: int = retry_state.kwargs.get("user_id")
    file_db_id: int = retry_state.kwargs.get("file_db_id")
    try:
        class_instance.delete_document(user_id=user_id, file_id=file_db_id)
    except Exception:
        logger.exception(
            f"Error occured while cleaning up User's {user_id} file {file_db_id} from Chroma DB"
        )


def cleanup_and_log_final_retry_failure(retry_state):
    """Handle exhausted retries and clean up document chunks from ChromaDB.

    Logs the original exception after all retry attempts have failed.
    Attempts to remove the associated document chunks from the vector
    database to prevent partially indexed documents from remaining.

    Cleanup failures are logged without masking the original exception.

    Args:
        retry_state (RetryCallState): Tenacity retry state containing
            the final exception, instance reference, and document identifiers.

    Raises:
        Exception: Re-raises the original exception that caused
            the indexing operation to fail.
    """
    error = retry_state.outcome.exception()

    logger.opt(exception=error).error(
        f"All retry attempts failed ({retry_state.attempt_number}). "
        f"Document was not indexed. Error: {error}"
    )
    class_instance = retry_state.args[0]
    user_id: int = retry_state.kwargs.get("user_id")
    file_db_id: int = retry_state.kwargs.get("file_db_id")
    try:
        class_instance.delete_document(user_id=user_id, file_id=file_db_id)
    except Exception:
        logger.exception(
            f"Error occured while cleaning up User's {user_id} file {file_db_id} from Chroma DB"
        )
    raise error


#! POSTGRESS
def log_and_delete_file(retry_state):
    """Handle exhausted retries when updating file metadata in PostgreSQL.

    Logs the original database operation failure and attempts to mark
    the associated file for deletion before removing its metadata
    from the database.

    Cleanup operations are executed independently. Failures during
    status updates or metadata deletion are logged without masking
    the original exception.

    Args:
        retry_state (RetryCallState): Tenacity retry state containing
            the original exception, repository instance, and file identifiers.

    Raises:
        Exception: Re-raises the original exception that caused
            the database operation to fail.
    """
    from backend.database.file_repository import FileRepository

    class_instance: FileRepository = retry_state.args[0]
    error = retry_state.outcome.exception()
    user_id: int = retry_state.kwargs.get("user_id")
    file_id: int = retry_state.kwargs.get("file_id")

    logger.opt(exception=error).error(
        f"All retry attempts failed for user {user_id}. "
        f"Update of document {file_id} metadata was not saved in DB:"
    )

    try:
        class_instance.mark_file_status_to_delte(file_id=file_id, user_id=user_id)
    except Exception:
        logger.exception(
            f"Cound not mark User's {user_id} file {file_id} to delte. Proceeding with file deletion anyway."
        )

    try:
        class_instance.delete_file_from_db(file_id=file_id, user_id=user_id)
    except Exception:
        logger.exception(f"Cound not delte User's {user_id} file {file_id} from DB")

    raise error


def _mark_file_to_del_tenacity_callback(retry_state):
    """Handle exhausted retries by marking and deleting file metadata.

    Called after all retry attempts have failed. Attempts to mark
    the associated file for deletion and remove its metadata from
    PostgreSQL.

    Each cleanup operation is handled independently to ensure that
    a failure in one operation does not prevent the next cleanup attempt.

    Cleanup exceptions are logged and suppressed to preserve
    the original operation failure.

    Args:
        retry_state (RetryCallState): Tenacity retry state containing
            the original exception, instance reference, and file identifiers.

    Raises:
        Exception: Re-raises the original exception that caused
            the operation to fail.
    """
    error = retry_state.outcome.exception()
    class_instance = retry_state.args[0]  # it contains self
    file_id: int = retry_state.kwargs.get("file_id")
    user_id: int = retry_state.kwargs.get("user_id")
    logger.error(
        f"After multiple retry attempts could not save User's {user_id} file {file_id} to storage. Deleting file metadata from DB in progress."
    )

    try:
        class_instance.mark_file_status_to_delte(file_id=file_id, user_id=user_id)
    except Exception:
        logger.exception(
            f"Cound not mark User's {user_id} file {file_id} to delte. Proceeding with file deletion anyway."
        )

    try:
        class_instance.delete_file_from_db(file_id=file_id, user_id=user_id)
    except Exception:
        logger.exception(f"Failed to delete User's {user_id} file {file_id} from DB.")

    raise error  # allways raise orginal error
