from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations
from backend.dependencies.depends import get_db


def test_get_conversations_ids_happy(client):
    """Function test get_conversations_ids endpint with happy path.
    It assumes User with ID = 1 exists.

    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """

    # Test setup
    session = client.app.state.session_maker()
    for _ in range(11):
        c = Conversations(user_id=1)
        session.add(c)
        session.commit()

    response = client.get("v1/get_conversations_ids?user_id=1")
    assert response.status_code == 200
    assert response.json() == [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]


def test_get_conversations_ids_less_than_10(client):
    """Function test get_conversations_ids endpint with happy path but less then 10 conversations
    It assumes User with ID = 1 exists.

    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """

    # Test setup
    session = client.app.state.session_maker()
    for _ in range(5):
        c = Conversations(user_id=1)
        session.add(c)
        session.commit()

    response = client.get("v1/get_conversations_ids?user_id=1")
    assert response.status_code == 200
    assert response.json() == [5, 4, 3, 2, 1]


def test_get_conversations_ids_no_conversations(client):
    """Function test get_conversations_ids endpint with happy path but with 0 conversations
    It assumes User with ID = 1 exists.

    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """
    response = client.get("v1/get_conversations_ids?user_id=1")
    assert response.status_code == 404


def test_get_conversations_ids_DB_error(client):
    """Function test get_conversations_ids endpint with DB error
    It assumes User with ID = 1 exists.

    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """
    # Test setup
    session_mock = Mock()
    session_mock.query.side_effect = SQLAlchemyError()

    client.app.dependency_overrides[get_db] = lambda: session_mock
    # Test
    response = client.get("v1/get_conversations_ids?user_id=1")

    assert response.status_code == 500

    client.app.dependency_overrides.clear()
