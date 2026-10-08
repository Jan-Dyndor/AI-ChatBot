from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger

from backend.api.schemas.pydantic_schemas import (
    ChatMessage,
    CreateUserRequest,
    CreateUserResponse,
    Models,
    Token,
    UploadFileResponse,
    UserDB,
    UserInput,
    UserLogin,
)
from backend.authentication.auth import AuthService
from backend.configuration.settings import Settings, get_settings
from backend.core.concurency.conversation_thread_lock import ConversationLockManager
from backend.dependencies.depends import (
    create_file_vector_storage,
    get_auth_service,
    get_chat_service,
    get_current_user,
    get_file_service,
    get_thread_lock,
    get_user_service,
)
from backend.exceptions.exc import ConversationIDConflict, NotEnoughtFileParameters
from backend.service.chat_service import ChatService
from backend.service.file_service import FileService
from backend.service.user_service import UserService
from RAG.file_vector_repository import FileVectorStorage

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


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
) -> list[tuple]:
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


@router.get("/models", response_model=Models)
def show_models(service: ChatService = Depends(get_chat_service)):
    return service.show_avaliable_models()


@router.post("/file", response_model=UploadFileResponse)
def upload_file(
    background_task: BackgroundTasks,
    file: UploadFile,
    file_service: FileService = Depends(get_file_service),
    user: UserDB = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    vector_file_storage: FileVectorStorage = Depends(create_file_vector_storage),
):

    if file.filename is None:
        raise NotEnoughtFileParameters(user_id=user.id, file_param="file name")
    if file.size is None:
        raise NotEnoughtFileParameters(user_id=user.id, file_param="file size")

    file_service.validate_file_size(
        size=file.size,
        max_size=settings.max_file_size_BYTES,
        user_id=user.id,
        file_name=file.filename,
    )

    safe_file_name = str(Path(file.filename).name)

    saved_file_path = file_service.save_file(
        file, file_name=safe_file_name, user_id=user.id
    )

    #! background task - embed document
    background_task.add_task(
        vector_file_storage.add_document, file_path=saved_file_path, user_id=user.id
    )

    return UploadFileResponse(file_name=safe_file_name)


@router.post("/chat")
def rag_caht(
    user_input: UserInput,
    service: ChatService = Depends(get_chat_service),
    user: UserDB = Depends(get_current_user),
    thread_lock: ConversationLockManager = Depends(get_thread_lock),
):

    lock = thread_lock.get_or_create_lock(conversation_id=user_input.conversation_id)
    if lock.acquire(blocking=False):
        try:

            service.save_user_input(
                user_input=user_input.input,
                conversation_id=user_input.conversation_id,
                user_id=user.id,
            )

            service.conversation_summary(
                user_input=user_input.input,
                conversation_id=user_input.conversation_id,
                model=user_input.model,
                user_id=user.id,
            )

            chat_history = service.fetch_chat_history(
                conversation_id=user_input.conversation_id, user_id=user.id
            )
        except Exception:
            logger.warning("Relase LOCK due to the error")
            lock.release()
            raise

        return StreamingResponse(
            service.thread_safe_rag_streaming_response(
                model=user_input.model,
                conversation_id=user_input.conversation_id,
                user_id=user.id,
                temperature=user_input.model_parameters.temperature,
                top_k=user_input.model_parameters.top_k,
                top_p=user_input.model_parameters.top_p,
                num_ctx=user_input.model_parameters.num_ctx,
                num_predict=user_input.model_parameters.num_predict,
                repeat_penalty=user_input.model_parameters.repeat_penalty,
                is_thinking=user_input.model_parameters.is_thinking,
                chat_history=chat_history,
                question=user_input.input,
                lock_object=lock,
            ),
            media_type="text/plain",
        )

    else:
        raise ConversationIDConflict(conversation_id=user_input.conversation_id)
