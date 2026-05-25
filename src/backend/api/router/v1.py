from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.api.schemas.pydantic_schemas import (
    ChatMessage,
    CreateUserRequest,
    CreateUserResponse,
    UserInput,
)
from backend.dependencies.depends import get_chat_service
from backend.service.chat_service import ChatService

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(
    user_input: UserInput,
    user_id_input: int,
    service: ChatService = Depends(get_chat_service),
):
    return StreamingResponse(
        service.stream_response_from_client(
            model=user_input.model,
            chat_history=user_input.chat_history,
            user_input=user_input.input,
            conversation_id=user_input.conversation_id,
            user_id=user_id_input,
        ),
        media_type="text/plain",
        headers={"Content-Type": "text/event-stream"},
    )


@router.get("/chat_history", response_model=list[ChatMessage])
def chat_history(
    conversation_id: int,
    user_id_input: int,
    service: ChatService = Depends(get_chat_service),
):
    return service.show_chat_history(conversation_id, user_id=user_id_input)


@router.get("/create_conversation")
def create_conversation(
    user_id_input: int,
    id: int | None = None,
    service: ChatService = Depends(get_chat_service),
) -> int:
    return service.create_conversation(user_id=user_id_input)


@router.get("/get_conversations_ids")
def get_conversetions_ids(
    user_id_input: int,
    service: ChatService = Depends(get_chat_service),
) -> list[int]:
    return service.lates_conversations_ids(user_id=user_id_input)


@router.post("/create_user", response_model=CreateUserResponse)
def create_user(
    user_data: CreateUserRequest, service: ChatService = Depends(get_chat_service)
):
    email = service.create_user(user_data.email, user_data.password)
    return CreateUserResponse(user_email=email)
