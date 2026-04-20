from fastapi import FastAPI
from backend.api.router.v1 import router
from contextlib import asynccontextmanager
from backend.configuration.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before app starts
    get_settings()  # read .env file
    yield
    # After shutdown


app = FastAPI()
app.include_router(router)
