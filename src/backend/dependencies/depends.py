from fastapi import Depends, Request

from backend.authentication.auth import AuthService, oauth2_scheme
from backend.database.chat_repository import ChatRepository
from backend.database.user_repository import UserRepository
from backend.service.chat_service import ChatService
from backend.service.user_service import UserService


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


#! User Repository


def get_user_repo(db=Depends(get_db)):
    return UserRepository(db_session=db)


#! AUTH


def get_auth_service(user_repo=Depends(get_user_repo)):
    return AuthService(user_repository=user_repo)


def get_current_user(
    token: str = Depends(oauth2_scheme), auth_service=Depends(get_auth_service)
):
    return auth_service.get_current_user_data(token)


#! User Service
def get_user_service(user_repo=Depends(get_user_repo)):
    return UserService(UserRepository=user_repo)
