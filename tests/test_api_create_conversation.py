from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Users
from backend.dependencies.depends import get_db


def test_create_conversation_happy(client):
    """Function tests API flow with ahppy path to create conversation

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
    """

    # Test setup
    session = client.app.state.session_maker()
    user = Users(email="test", password_hash="test")
    session.add(user)
    session.commit()

    assert session.query(Conversations).first() is None
    # Test
    result = client.get(f"v1/create_conversation?user_id={user.id}")
    conv = session.query(Conversations).first()

    assert result.json() == 1
    assert result.status_code == 200
    assert conv is not None
    assert conv.user_id == 1


def test_create_conversation_no_user(client):
    """Function tests endpoint behaviour when there is no user with user_id in DB

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
    """
    non_existing_user_id: int = 9999999
    result = client.get(f"v1/create_conversation?user_id={non_existing_user_id}")

    assert result.status_code == 404
    assert (
        result.json().get("message")
        == f"User with ID {non_existing_user_id} not found in DB"
    )


def test_create_conversation_db_error(client):
    """Function tests endpoint behaviour when the DB error occured

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
    """

    # Test setup
    session = client.app.state.session_maker()
    user = Users(email="test", password_hash="test")
    session.add(user)
    session.commit()

    session_mock = Mock()
    session_mock.add.side_effect = SQLAlchemyError()

    # Test
    client.app.dependency_overrides[get_db] = lambda: session_mock

    result = client.get(f"v1/create_conversation?user_id={user.id}")

    assert result.status_code == 500
    assert result.json().get("message") == "Database operation failed"
    session_mock.rollback.assert_called_once()

    client.app.dependency_overrides.clear()
