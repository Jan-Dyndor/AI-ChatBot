from fastapi import FastAPI, Request
from backend.exceptions.exc import AppExceptions
from fastapi.responses import JSONResponse
from backend.configuration.logging_config import logger


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(AppExceptions)
    async def app_exception_handler(request: Request, exc: AppExceptions):
        logger.opt(exception=exc).error(
            f"Application error: {exc.status_code} - {exc.message}. Path - {request.url.path},  method - {request.method}"
        )
        return JSONResponse(
            status_code=exc.status_code, content={"message": exc.message}
        )
