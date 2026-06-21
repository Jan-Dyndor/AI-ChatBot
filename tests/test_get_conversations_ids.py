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
        c = Conversations(user_id=test_user_db.id, summary=f"{_+1} test")
        session.add(c)
        session.commit()

    response = client.get(
        "v1/conversations", headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert response.status_code == 200
    # in backend this is list[tuple] but after JSON HTTP response it is list[list]
    assert response.json() == [
        [11, "11 test"],
        [10, "10 test"],
        [9, "9 test"],
        [8, "8 test"],
        [7, "7 test"],
        [6, "6 test"],
        [5, "5 test"],
        [4, "4 test"],
        [3, "3 test"],
        [2, "2 test"],
    ]


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
        c = Conversations(user_id=test_user_db.id, summary=f"{_+1} test")
        session.add(c)
        session.commit()

    response = client.get(
        "v1/conversations", headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert response.json() == [
        [5, "5 test"],
        [4, "4 test"],
        [3, "3 test"],
        [2, "2 test"],
        [1, "1 test"],
    ]


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
        "v1/conversations", headers={"Authorization": f"Bearer {valid_token}"}
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
        "v1/conversations", headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert response.status_code == 500


#! Invalid token
def test_conversations_ids_invalid_token(client, invalid_token):
    """Function tests invalid token to endpoint GET conversations

    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
        invalid_token (_type_): JWT
    """
    response = client.get(
        "v1/conversations", headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert response.status_code == 401
