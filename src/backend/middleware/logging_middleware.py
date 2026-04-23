from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from loguru import logger
import time


class LoggingMiddleware(BaseHTTPMiddleware):
    """Adds request ID into logs"""

    async def dispatch(self, request: Request, call_next) -> Response:

        request_id = request.state.request_id

        method = request.method
        path = request.url.path
        start = time.perf_counter()

        with logger.contextualize(request_id=request_id):
            logger.info(f"Incoming {method} {path}")

            response = await call_next(request)

            duration = (time.perf_counter() - start) * 1000

            logger.info(
                f"Completed {method} {path} with status {response.status_code} in {duration:.2f}"
            )
            return response
