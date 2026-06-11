from fastapi import FastAPI, Request
from backend.exceptions.exc import AppExceptions
from fastapi.responses import JSONResponse
from backend.configuration.logging_config import logger
from fastapi.exceptions import RequestValidationError


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(AppExceptions)
    async def app_exception_handler(request: Request, exc: AppExceptions):
        if exc.status_code in range(400, 500):
            logger.warning(  # just info no traceback
                f"Application error: {exc.status_code} - {exc.message}. Path - {request.url.path},  method - {request.method}"
            )
        else:
            # info + traceback
            logger.opt(exception=exc).error(
                f"Application error: {exc.status_code} - {exc.message}. Path - {request.url.path},  method - {request.method}"
            )
        return JSONResponse(
            status_code=exc.status_code, content={"message": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def app_exception_handler_validation(
        request: Request, exception: RequestValidationError
    ):
        error_mess = exception.errors()[0]["msg"]
        logger.warning(
            f"Validation error: - {error_mess} Path - {request.url.path},  method - {request.method}"
        )
        return JSONResponse(status_code=422, content=error_mess)
