from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router.v1 import router
from backend.configuration.logging_config import set_up_logging
from backend.configuration.settings import get_settings
from backend.database.db import Base, session_factory, get_engine
from backend.exceptions.handlers import register_exception_handlers
from backend.middleware.logging_middleware import LoggingMiddleware
from backend.middleware.request_id_middleware import RequestIDMiddleware

set_up_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings.cache_clear()
    # Before app starts
    settings = get_settings()  # read .env file
    app.state.settings = settings
    engine = get_engine(settings.db_url)
    Base.metadata.create_all(bind=engine)
    session_maker = session_factory(engine)
    app.state.session_maker = session_maker
    yield
    # After shutdown
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(router)
    register_exception_handlers(app)

    return app


app = create_app()
