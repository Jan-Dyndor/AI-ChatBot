from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds a unique ID to each Request and saves it in headers for frontend tracing"""

    async def dispatch(self, request: Request, call_next) -> Response:

        request_id = request.headers.get("Request-ID")

        if not request_id:
            request_id = str(uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["Request-ID"] = request_id

        return response
