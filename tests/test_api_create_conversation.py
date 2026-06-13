from unittest.mock import Mock, patch

from sqlalchemy.exc import SQLAlchemyError

from backend.database.chat_repository import ChatRepository
from backend.database.models import Conversations, Users
from backend.dependencies.depends import get_db
from backend.exceptions.exc import DataBaseError


#! Valid token
def test_create_conversation_happy(client, valid_token, test_user_db):
    """Function tests API flow with ahppy path to create conversation

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        valid_token (JWT): JWT token
        test_user_db (Users): user
    """
    # Test setup
    session = client.app.state.session_maker()
    session.add(test_user_db)
    session.commit()

    assert session.query(Conversations).first() is None
    # Test
    result = client.get(
        "v1/create_conversation", headers={"Authorization": f"Bearer {valid_token}"}
    )
    conv = session.query(Conversations).first()

    assert result.json() == 1
    assert result.status_code == 200
    assert conv is not None
    assert conv.user_id == 1


def test_create_conversation_no_user(client, valid_token):
    """Function tests endpoint behaviour when there is no user with user_id in DB (somehow)

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        valid_token (JWT): JWT token
        test_user_db (Users): user
    """

    result = client.get(
        "v1/create_conversation", headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert result.status_code == 401


@patch.object(ChatRepository, "create_conversation")
def test_create_conversation_db_error(
    mock_chat_repo, client, test_user_db, valid_token
):
    """Function tests endpoint behaviour when the DB error occured

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        valid_token (JWT): JWT token
        test_user_db (Users): user
    """

    mock_chat_repo.side_effect = DataBaseError()
    # Test setup
    session = client.app.state.session_maker()
    session.add(test_user_db)
    session.commit()

    result = client.get(
        "v1/create_conversation", headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert result.status_code == 500


# In above test I can not mock get_db since AUTH is using it
# I can not also mock get_chat_repo since I would have to return ChatRepository object not raise an error
# So the only option is to mock a function in ChatRepository that will return my custom DataBaseError htat occures when SQLAlchemyError happens


#! Invalid token
def test_invalid_token(client, invalid_token, test_user_db):
    """Function test invalid token

    Args:
     client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
     valid_token (JWT): JWT token
     test_user_db (Users): user
    """

    session = client.app.state.session_maker()
    session.add(test_user_db)
    session.commit()

    result = client.get(
        "v1/create_conversation", headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert result.status_code == 401
