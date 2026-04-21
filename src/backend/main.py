from fastapi import FastAPI
from backend.api.router.v1 import router
from contextlib import asynccontextmanager
from backend.configuration.settings import get_settings
from backend.configuration.logging_config import set_up_logging


set_up_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before app starts
    get_settings()  # read .env file
    yield
    # After shutdown


app = FastAPI(lifespan=lifespan)
app.include_router(router)
