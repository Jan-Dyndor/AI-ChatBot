from datetime import timedelta
from pathlib import Path

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from pydantic import ValidationError
from redis.exceptions import LockNotOwnedError
from sse_starlette import EventSourceResponse

from backend.api.schemas.pydantic_schemas import (
    CeleryTaskUpdateResponse,
    ChatMessage,
    CreateUserRequest,
    CreateUserResponse,
    FilesResponse,
    Models,
    Token,
    UploadFileResponse,
    UserDB,
    UserInput,
    UserLogin,
)
from backend.authentication.auth import AuthService
from backend.celery_app.celery_app import celery_app
from backend.celery_app.celery_tasks import index_and_save_file
from backend.configuration.settings import Settings
from backend.dependencies.depends import (
    create_file_vector_storage,
    get_auth_service,
    get_chat_service,
    get_current_user,
    get_file_service,
    get_redis_client,
    get_request_id,
    get_settings,
    get_user_service,
)
from backend.exceptions.exc import (
    ConversationIDConflict,
    NotEnoughtFileParameters,
    ValidationErrorCredentials,
)
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
    user_data=Depends(OAuth2PasswordRequestForm),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    try:
        valid_user_data = UserLogin.model_validate(
            {"username": user_data.username, "password": user_data.password}
        )
    except ValidationError as e:
        variable_name = e.errors()[0]["loc"][0]
        issue_message: str = e.errors()[0]["msg"]
        raise ValidationErrorCredentials(variable_name, issue_message) from e

    user = auth_service.authenticate_user(
        user_email=valid_user_data.username, password=valid_user_data.password
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


@router.post(
    "/file", response_model=UploadFileResponse, status_code=status.HTTP_202_ACCEPTED
)
def upload_file(
    file: UploadFile,
    file_service: FileService = Depends(get_file_service),
    user: UserDB = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    request_id: str = Depends(get_request_id),
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

    file_bytes: bytes = file.file.read()

    sha: str = file_service.validate_if_file_exists(
        user_id=user.id,
        file_name=file.filename,
        file_bytes=file_bytes,
    )

    file_id_db: int = file_service.save_partially_file_metadata(
        user_id=user.id, file_name=file.filename, sha=sha, task_id=request_id
    )

    safe_file_name = str(Path(file.filename).name)

    saved_file_path: Path = file_service.update_and_save_file_metadata(
        file=file, file_name=safe_file_name, user_id=user.id, file_id=file_id_db
    )

    #! CELERY TASK
    task = index_and_save_file.apply_async(  # type: ignore
        kwargs={
            "file_path": str(saved_file_path),
            "user_id": user.id,
            "request_id": request_id,
            "file_id": file_id_db,
        },
        task_id=request_id,
    )
    return UploadFileResponse(file_name=safe_file_name, request_id=task.id)


@router.post("/chat")
def rag_chat(
    user_input: UserInput,
    service: ChatService = Depends(get_chat_service),
    user: UserDB = Depends(get_current_user),
    redis_client=Depends(get_redis_client),
):

    lock = redis_client.lock(
        name=f"lock:conversation:{user_input.conversation_id}",
        timeout=300,  # 5 min TTL
        blocking=False,
        thread_local=False,
    )

    if lock.acquire():
        try:
            service.conversation_summary(
                user_input=user_input.input,
                conversation_id=user_input.conversation_id,
                model=user_input.model,
                user_id=user.id,
            )

            chat_history = service.fetch_chat_history(
                conversation_id=user_input.conversation_id, user_id=user.id
            )

            user_message_id: int = service.save_user_input(
                user_input=user_input.input,
                conversation_id=user_input.conversation_id,
                user_id=user.id,
            )

            return EventSourceResponse(
                service.redis_locked_rag_streaming_response(
                    user_message_id=user_message_id,
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
                )
            )

        except Exception:
            try:
                lock.release()
            except LockNotOwnedError:
                logger.error(
                    f"User's {user.id} conversation {user_input.conversation_id} request lost the Lock object"
                )
            logger.exception(
                f"Exception occured file processing User's {user.id} request. Releasing REDIS LOCK"
            )
            raise
    else:
        raise ConversationIDConflict(conversation_id=user_input.conversation_id)


@router.get("/files", response_model=list[FilesResponse] | None)
def get_files(
    user: UserDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    return file_service.get_all_users_files(user.id)


@router.get(
    "/files/{file_id}",
    response_class=FileResponse,
)
def get_file(
    file_id: int,
    user: UserDB = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):

    file_path: Path = Path(file_service.get_file(user_id=user.id, file_id=file_id))
    return file_path


@router.get("/tasks/{task_id}")
def check_celery_task(task_id: str):
    result = AsyncResult(id=task_id, app=celery_app)
    return CeleryTaskUpdateResponse(task_id=task_id, state=result.state)


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    user: UserDB = Depends(get_current_user),
    file_servce: FileService = Depends(get_file_service),
    file_vector_storage: FileVectorStorage = Depends(create_file_vector_storage),
):
    file_servce.prepare_to_del_file_from_db(user_id=user.id, file_id=file_id)

    file_vector_storage.delete_document(user_id=user.id, file_id=file_id)

    file_servce.delete_file_from_db(user_id=user.id, file_id=file_id)
