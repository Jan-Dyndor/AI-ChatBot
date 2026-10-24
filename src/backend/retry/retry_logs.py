from pathlib import Path

from loguru import logger


def log_retry(retry_state):
    logger.warning(
        f"Retry attempt {retry_state.attempt_number} failed. "
        f"Error: {retry_state.outcome.exception()}"
    )


def log_final_retry_failure(retry_state):
    error = retry_state.outcome.exception()

    logger.opt(exception=error).error(
        f"All retry attempts failed ({retry_state.attempt_number}). "
        f"Document was not indexed. Error: {error}"
    )
    raise error


def log_and_delete_file(retry_state):
    from backend.database.file_repository import FileRepository

    error = retry_state.outcome.exception()
    file_path = Path(retry_state.kwargs["file_path"])
    user_id = retry_state.kwargs["user_id"]

    logger.opt(exception=error).error(
        f"All retry attempts failed for user {user_id}. "
        f"Document metadata was not saved in DB: {file_path}"
    )

    try:
        FileRepository.delete_file_from_storage(file_path)
        logger.warning(f"Deleted file after failed DB save: {file_path}")
    except OSError as cleanup_error:
        logger.opt(exception=cleanup_error).error(
            f"Could not delete file after failed indexing: {file_path}. Need to do it manually."
        )

    raise error
