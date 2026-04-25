from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router.v1 import router
from backend.configuration.logging_config import set_up_logging
from backend.configuration.settings import Settings, get_settings
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.middleware.request_id_middleware import RequestIDMiddleware

set_up_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings.cache_clear()
    # Before app starts
    get_settings()  # read .env file
    yield
    # After shutdown


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(router)

    return app


app = create_app()
