import time

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


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
                f"Outgoing HTTP {method} {path} -> {response.status_code} response created in {duration:.2f} ms "
            )
            return response
