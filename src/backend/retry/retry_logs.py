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
