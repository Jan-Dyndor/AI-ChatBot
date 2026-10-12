from fastapi import Depends, Request
from langchain_core.vectorstores import VectorStore

from backend.authentication.auth import AuthService, oauth2_scheme
from backend.chat_bot.client import ChatBotClient
from backend.configuration.settings import Settings
from backend.database.chat_repository import ChatRepository
from backend.database.file_repository import FileRepository
from backend.database.user_repository import UserRepository
from backend.service.chat_service import ChatService
from backend.service.file_service import FileService
from backend.service.user_service import UserService
from RAG.document_indexing_seervice import DocumentIndexingService
from RAG.file_vector_repository import FileVectorStorage


def get_db(request: Request):
    """Function uses sesionmaker to return DB session object

    Yields:
        _type_: session object
    """

    db = request.app.state.session_maker()
    try:
        yield db
    finally:
        db.close()


def get_chat_repo(db=Depends(get_db)) -> ChatRepository:
    """Function is used to create ChatRepository object that needs to have database session parameter whitch is provided by get_db function.
    It chains the Depends function of FastAPI

    Args:
        db: Session object from session maker.

    Returns:
        ChatRepository: object used to do operations on DB
    """
    return ChatRepository(db_session=db)


def get_chat_bot_client() -> ChatBotClient:
    """Function is used to create ChatBotClient object that has methods to communicate with Ollama.
    It chains the Depends function of FastAPI

    Returns:
        ChatBotClient: Object of Ollama client
    """
    return ChatBotClient()


#! Settings
def get_settings(request: Request):
    return request.app.state.settings


#! User Repository


def get_user_repo(db=Depends(get_db)):
    return UserRepository(db_session=db)


#! AUTH


def get_auth_service(user_repo=Depends(get_user_repo), settings=Depends(get_settings)):
    return AuthService(user_repository=user_repo, settings=settings)


def get_current_user(
    token: str = Depends(oauth2_scheme), auth_service=Depends(get_auth_service)
):
    return auth_service.get_current_user_data(token)


#! User Service
def get_user_service(user_repo=Depends(get_user_repo)):
    return UserService(UserRepository=user_repo)


#! Thread Lock
def get_thread_lock(request: Request):
    return request.app.state.lock


# ! Files
def get_file_repo(db_session=Depends(get_db)):
    return FileRepository(db_session)


def get_file_service(file_repository=Depends(get_file_repo)):
    return FileService(file_repository)


#! vector store


def get_vector_storage(request: Request):
    return request.app.state.vector_store


def get_indexing_service(settings: Settings = Depends(get_settings)):
    return DocumentIndexingService(
        chunk_overlap=settings.chunk_overlap, chunk_size=settings.chunk_size
    )


def create_file_vector_storage(
    indexing_service: DocumentIndexingService = Depends(get_indexing_service),
    vector_store: VectorStore = Depends(get_vector_storage),
) -> FileVectorStorage:
    return FileVectorStorage(
        vector_db=vector_store, file_index_service=indexing_service
    )


def get_chat_service(
    repository=Depends(get_chat_repo),
    chat_bot_client=Depends(get_chat_bot_client),
    file_vector_storage: FileVectorStorage = Depends(create_file_vector_storage),
) -> ChatService:
    """Function is used to create ChatService object that needs to have ChatRepository parameter whitch is provided by get_get_chat_repo  function.
    ChatService is required in endpoint since it contains all business logic.
    It chains the Depends function of FastAPI

    Args:
        repository (ChatRepository): Object to do all DB operations.

    Returns:
        ChatService: object that contains all business logic
    """
    return ChatService(
        db=repository,
        chat_bot_client=chat_bot_client,
        file_vector_storage=file_vector_storage,
    )
