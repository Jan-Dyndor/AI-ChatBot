from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.schemas.pydantic_schemas import UserInput, ChatMessage
from backend.service.chat_service import ChatService
from fastapi import Depends
from src.backend.dependencies.depends import get_chat_service, get_db

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(user_input: UserInput, service: ChatService = Depends(get_chat_service)):
    return StreamingResponse(
        service.stream_response_from_client(
            model=user_input.model,
            chat_history=user_input.chat_history,
            user_input=user_input.input,
        ),
        media_type="text/plain",
        headers={"Content-Type": "text/event-stream"},
    )


@router.get("/chat_history", response_model=list[ChatMessage])
def chat_history(service: ChatService = Depends(get_chat_service)):
    return service.show_chat_history()
