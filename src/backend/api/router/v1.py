from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.schemas.pydantic_schemas import UserInput
from backend.chat_bot.client import ai_bot

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(user_input: UserInput):
    return StreamingResponse(
        ai_bot.stream_response(user_input.input), media_type="text/plain"
    )
