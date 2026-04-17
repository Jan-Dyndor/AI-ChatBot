from fastapi import FastAPI
from backend.api.router.v1 import router

app = FastAPI()
app.include_router(router)
