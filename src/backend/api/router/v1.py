from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.api.schemas.pydantic_schemas import ChatMessage, UserInput
from backend.service.chat_service import ChatService
from backend.dependencies.depends import get_chat_service, get_db

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(
    user_input: UserInput,
    service: ChatService = Depends(get_chat_service),
):
    return StreamingResponse(
        service.stream_response_from_client(
            model=user_input.model,
            chat_history=user_input.chat_history,
            user_input=user_input.input,
            conversation_id=user_input.conversation_id,
        ),
        media_type="text/plain",
        headers={"Content-Type": "text/event-stream"},
    )


@router.get("/chat_history", response_model=list[ChatMessage])
def chat_history(
    conversation_id: int, service: ChatService = Depends(get_chat_service)
):
    return service.show_chat_history(conversation_id)


@router.get("/create_conversation_id")
def get_conversation_id(
    id: int | None = None, service: ChatService = Depends(get_chat_service)
):
    return service.return_conversation_id()
