from unittest.mock import patch

from backend.database.chat_repository import ChatRepository
from backend.database.models import Conversations
from backend.exceptions.exc import DataBaseError


#! Valid token
def test_get_conversations_ids_happy(client, test_user_db, valid_token):
    """Function test get_conversations_ids endpint with happy path.
    It assumes User with ID = 1 exists.

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
        test_user_db (Users): User
        valid_token (JWT): JWT
    """

    # Test setup
    session = client.app.state.session_maker()
    session.add(test_user_db)
    session.commit()

    for _ in range(11):
        c = Conversations(user_id=test_user_db.id)
        session.add(c)
        session.commit()

    response = client.get(
        "v1/get_conversations_ids", headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert response.json() == [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]


def test_get_conversations_ids_less_than_10(client, test_user_db, valid_token):
    """Function test get_conversations_ids endpint with happy path but less then 10 conversations
    It assumes User with ID = 1 exists.

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
        test_user_db (Users): User
        valid_token (JWT): JWT
    """

    # Test setup
    session = client.app.state.session_maker()
    session.add(test_user_db)
    session.commit()

    for _ in range(5):
        c = Conversations(user_id=test_user_db.id)
        session.add(c)
        session.commit()

    response = client.get(
        "v1/get_conversations_ids", headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert response.json() == [5, 4, 3, 2, 1]


def test_get_conversations_ids_no_conversations(client, valid_token, test_user_db):
    """Function test get_conversations_ids endpint with happy path but with 0 conversations
    It assumes User with ID = 1 exists.

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
        test_user_db (Users): User
        valid_token (JWT): JWT
    """
    session = client.app.state.session_maker()
    session.add(test_user_db)
    session.commit()

    response = client.get(
        "v1/get_conversations_ids", headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 404


@patch.object(ChatRepository, "user_lates_conversations_ids")
def test_get_conversations_ids_DB_error(
    mock_chat_repo_user_lates_conversations_ids,
    client,
    valid_token,
    test_user_db,
):
    """Function test get_conversations_ids endpint with DB error
    It assumes User with ID = 1 exists.

    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """
    # Test setup
    session = client.app.state.session_maker()
    session.add(test_user_db)
    session.commit()

    mock_chat_repo_user_lates_conversations_ids.side_effect = DataBaseError()

    # Test
    response = client.get(
        "v1/get_conversations_ids", headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert response.status_code == 500
