from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Users
from backend.dependencies.depends import get_db


def test_create_user_happy(client):
    """Function test create user happy path
    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """

    session = client.app.state.session_maker()

    assert session.query(Users).first() is None

    response = client.post(
        "/v1/create_user", json={"email": "test@gmail.com", "password": "test_pass"}
    )

    assert response.status_code == 201
    assert session.query(Users).first() is not None
    assert response.json().get("email") == "test@gmail.com"


def test_create_user_user_already_exists(client):
    """Function test create user but user wtih that email already exists
    Args:
        client (_type_): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)
    """
    session = client.app.state.session_maker()

    user = Users(email="test@gmail.com", password_hash="123456789")
    session.add(user)
    session.commit()

    response = client.post(
        "/v1/create_user", json={"email": "test@gmail.com", "password": "test_pass"}
    )

    assert response.status_code == 409


def test_create_user_DB_error(client):
    session_mock = Mock()
    session_mock.query.side_effect = SQLAlchemyError()

    client.app.dependency_overrides[get_db] = lambda: session_mock

    response = client.post(
        "/v1/create_user", json={"email": "test@gmail.com", "password": "test_pass"}
    )

    assert response.status_code == 500
    client.app.dependency_overrides.clear()
