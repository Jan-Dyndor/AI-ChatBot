from fastapi import Depends

from backend.database.db import session_factory
from backend.database.repository import ChatRepository
from backend.service.chat_service import ChatService


def get_db():
    """Function uses sesionmaker to return DB session object

    Yields:
        _type_: session object
    """
    db = session_factory()
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


def get_chat_service(repository=Depends(get_chat_repo)) -> ChatService:
    """Function is used to create ChatService object that needs to have ChatRepository parameter whitch is provided by get_get_chat_repo  function.
    ChatService is required in endpoint since it contains all business logic.
    It chains the Depends function of FastAPI

    Args:
        repository (ChatRepository): Object to do all DB operations.

    Returns:
        ChatService: object that contains all business logic
    """
    return ChatService(db=repository)
