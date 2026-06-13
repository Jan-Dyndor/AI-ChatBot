from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Messages, Users
from backend.dependencies.depends import get_db


#! VALID JWT
def test_chat_history_happy(client, valid_token):
    """Function test chat_history endpoint with happy path.

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        valid_token (JWT): valid JWT
    """
    # Test prepare

    session = client.app.state.session_maker()
    user = Users(email="test@gmail.com", password_hash="test")
    session.add(user)
    session.commit()
    conversation = Conversations(user_id=user.id)
    session.add(conversation)
    session.commit()
    mess1 = Messages(
        conversation_id=conversation.id,
        role="assistant",
        content="How are you? I am AI!",
    )
    mess2 = Messages(
        conversation_id=conversation.id,
        role="user",
        content="I am ok, tell me about Arnold Schwarzenegger",
    )
    session.add_all([mess1, mess2])
    session.commit()

    # Test Body

    response = client.get(
        url="v1/chat_history?conversation_id=1",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    resp = response.json()
    assert response.status_code == 200
    assert response is not None
    assert isinstance(resp, list)
    assert resp[0].get("role") == "assistant"
    assert resp[1].get("role") == "user"
    assert len(resp) == 2


def test_chat_history_no_messages(client, valid_token):
    """Function test chat_history endpoint with no messages in conversation

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        valid_token (JWT): valid JWT"""
    # Test prepare

    session = client.app.state.session_maker()
    user = Users(email="test@gmail.com", password_hash="test")
    session.add(user)
    session.commit()
    conversation = Conversations(user_id=user.id)
    session.add(conversation)
    session.commit()

    response = client.get(
        url="v1/chat_history?conversation_id=1",
        headers={"Authorization": f"Bearer {valid_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_chat_history_co_conversation_or_wrong_userID(client, valid_token):
    """Function test chat_history endpoint when User does not own this conversation or there is no conversation with particular ID

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        valid_token (JWT): valid JWT
    """
    session = client.app.state.session_maker()
    user = Users(email="test@gmail.com", password_hash="test")
    session.add(user)
    session.commit()

    response = client.get(
        url="v1/chat_history?conversation_id=1",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 404
    assert response.json().get("message") == "Database cound not find given resource"


def test_chat_history_DB_error(client, valid_token):
    """Function test chat_history endpoint with Database related error

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        valid_token (JWT): valid JWT
    """

    session = client.app.state.session_maker()
    user = Users(email="test@gmail.com", password_hash="test")
    session.add(user)
    session.commit()

    session_mock = Mock()
    session_mock.query.side_effect = SQLAlchemyError()

    client.app.dependency_overrides[get_db] = lambda: session_mock

    response = client.get(
        url="v1/chat_history?conversation_id=1",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 500
    client.app.dependency_overrides.clear()


#! Invalid Token
def test_chat_history_invalid_token(client, invalid_token):
    """Test with Invalid token

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        invalid_token (JWT): invalid JWT
    """

    response = client.get(
        url="v1/chat_history?conversation_id=1",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 401
