from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.api.schemas.pydantic_schemas import (
    ChatMessage,
    CreateUserRequest,
    CreateUserResponse,
    Token,
    UserDB,
    UserInput,
    UserLogin,
)
from backend.authentication.auth import AuthService
from backend.configuration.settings import get_settings, Settings
from backend.dependencies.depends import (
    get_auth_service,
    get_chat_service,
    get_current_user,
    get_user_service,
)
from backend.service.chat_service import ChatService
from backend.service.user_service import UserService

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(
    user_input: UserInput,
    # user_id: int,
    service: ChatService = Depends(get_chat_service),
    user: UserDB = Depends(get_current_user),
):
    # Check User data before streaming response starts - after it starts it will not be possible to change status code + save user input to DB

    service.save_user_input(
        user_input=user_input.input,
        conversation_id=user_input.conversation_id,
        user_id=user.id,
    )

    # Start Streaming response
    return StreamingResponse(
        service.stream_response_from_client(
            model=user_input.model,
            chat_history=user_input.chat_history,
            conversation_id=user_input.conversation_id,
            user_id=user.id,
        ),
        media_type="text/plain",
        headers={"Content-Type": "text/event-stream"},
    )

    # After streaming


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[ChatMessage]
)
def chat_history(
    conversation_id: int,
    user: UserDB = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return service.show_chat_history(conversation_id, user_id=user.id)


@router.post("/conversations")
def create_conversation(
    user: UserDB = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> int:
    return service.create_conversation(user_id=user.id)


@router.get(
    "/conversations"
)  # Here was be default 10 lat updated conversations later I will add pagination so user can request more
def get_conversetions_ids(
    user: UserDB = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[int]:
    return service.lates_conversations_ids(user_id=user.id)


@router.post("/users", response_model=CreateUserResponse, status_code=201)
def create_user(
    user_data: CreateUserRequest, user_service: UserService = Depends(get_user_service)
):
    email = user_service.create_user(user_data.email, user_data.password)
    return CreateUserResponse(email=email)


@router.post("/token")
def login_for_access_token(
    user_data: UserLogin,
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    user = auth_service.authenticate_user(
        user_email=user_data.email, password=user_data.password
    )
    access_token_expires = timedelta(minutes=settings.token_expires_minutes)
    token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=CreateUserResponse)
def me(user: UserDB = Depends(get_current_user)):
    return user
