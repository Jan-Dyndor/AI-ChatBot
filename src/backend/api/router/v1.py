from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

from backend.api.schemas.pydantic_schemas import (
    ChatMessage,
    CreateUserRequest,
    CreateUserResponse,
    Token,
    UserInput,
    UserDB,
)

from backend.authentication.auth import AuthService
from backend.dependencies.depends import (
    get_auth_service,
    get_chat_service,
    get_user_service,
    get_current_user,
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


@router.get("/chat_history", response_model=list[ChatMessage])
def chat_history(
    conversation_id: int,
    user: UserDB = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    return service.show_chat_history(conversation_id, user_id=user.id)


@router.get("/create_conversation")
def create_conversation(
    user: UserDB = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> int:
    return service.create_conversation(user_id=user.id)


@router.get("/get_conversations_ids")
def get_conversetions_ids(
    user: UserDB = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[int]:
    return service.lates_conversations_ids(user_id=user.id)


@router.post("/create_user", response_model=CreateUserResponse, status_code=201)
def create_user(
    user_data: CreateUserRequest, user_service: UserService = Depends(get_user_service)
):
    email = user_service.create_user(user_data.email, user_data.password)
    return CreateUserResponse(email=email)


#! Nie wiem czy nie trzeba zmienci na query params zeby frontend mogl wysalc info
@router.post("/token")
def login_for_access_token(
    form_data=Depends(OAuth2PasswordRequestForm),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    user = auth_service.authenticate_user(
        user_email=form_data.username, password=form_data.password
    )
    access_token_expires = timedelta(minutes=30)  #! Potem do zmiany z settings
    token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=CreateUserResponse)
def me(user: UserDB = Depends(get_current_user)):
    return user
