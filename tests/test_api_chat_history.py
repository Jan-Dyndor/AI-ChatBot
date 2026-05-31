from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Messages, Users
from backend.dependencies.depends import get_db


def test_chat_history_happy(client):
    """Function test chat_history endpoint with happy path.


    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
    """
    # Test prepare

    session = client.app.state.session_maker()
    user = Users(email="test", password_hash="test")
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

    response = client.get(url="v1/chat_history?conversation_id=1&user_id=1")
    resp = response.json()
    assert response.status_code == 200
    assert response is not None
    assert isinstance(resp, list)
    assert resp[0].get("role") == "assistant"
    assert resp[1].get("role") == "user"
    assert len(resp) == 2


def test_chat_history_no_messages(client):
    """Function test chat_history endpoint with no messages in conversation


    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
    """
    # Test prepare

    session = client.app.state.session_maker()
    user = Users(email="test", password_hash="test")
    session.add(user)
    session.commit()
    conversation = Conversations(user_id=user.id)
    session.add(conversation)
    session.commit()

    response = client.get(url="v1/chat_history?conversation_id=1&user_id=1")

    assert response.status_code == 200
    assert response.json() == []


def test_chat_history_co_conversation_or_wrong_userID(client):
    """Function test chat_history endpoint when User does not own this conversation or there is no conversation with particular ID


    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """

    response = client.get(url="v1/chat_history?conversation_id=1&user_id=1")
    print(response.json())
    assert response.status_code == 404
    assert response.json().get("message") == "Database cound not find given resource"


def test_chat_history_DB_error(client):
    """Function test chat_history endpoint with Database related error

    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
    """

    session_mock = Mock()
    session_mock.query.side_effect = SQLAlchemyError()

    client.app.dependency_overrides[get_db] = lambda: session_mock

    response = client.get(url="v1/chat_history?conversation_id=1&user_id=1")
    assert response.status_code == 500
    client.app.dependency_overrides.clear()
