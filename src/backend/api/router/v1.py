from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.schemas.pydantic_schemas import UserInput
from backend.chat_bot.client import ChatBot

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(user_input: UserInput):
    ai_bot = ChatBot(user_input.model)

    return StreamingResponse(
        ai_bot.stream_response(chat_history=user_input.chat_history),
        media_type="text/plain",
    )
