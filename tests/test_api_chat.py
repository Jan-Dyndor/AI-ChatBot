from unittest.mock import Mock, patch

import sseclient

from backend.api.schemas.pydantic_schemas import UserDB
from backend.database.models import Users
from backend.dependencies.depends import (
    get_chat_repo,
    get_chat_service,
    get_current_user,
)
from backend.exceptions.exc import DataBaseResourceNotFound
from backend.service.chat_service import ChatService


#! VALID TOKEN
def test_chat_wrong_user_input(client, wrong_user_input_empty, valid_token):
    """Test API call with no user input

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware adn router)
        wrong_user_input_empty (dict): wrong user input to API
        valid_token (JWT): valid JWT
    """

    session = client.app.state.session_maker()

    user = Users(email="test@gmail.com", password_hash="test")
    session.add(user)
    session.commit()

    response = client.post(
        "v1/chat",
        json=wrong_user_input_empty,
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 422


def test_chat_wrong_user_input_long(client, wrong_user_input_too_long, valid_token):

    session = client.app.state.session_maker()
    user = Users(email="test@gmail.com", password_hash="test")
    session.add(user)
    session.commit()

    response = client.post(
        "v1/chat",
        json=wrong_user_input_too_long,
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 422


def test_chat_streaming_save_user_input_error(
    client, happy_test_user_input_short, valid_token
):
    """Function tests API response when there is an error within save_user_input_function

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)

        happy_test_user_input_short (UserInput): ficxture tyo store user input and chat histroy, successfully converted into Pydantic models
    """
    service = Mock(spec=ChatService)
    service.fetch_chat_history.return_value = []
    service.save_user_input.side_effect = DataBaseResourceNotFound()
    client.app.dependency_overrides[get_chat_service] = lambda: service
    client.app.dependency_overrides[get_current_user] = lambda: UserDB(
        id=1, email="test@gmail.com", password_hash="test"
    )

    response = client.post(
        "v1/chat",
        json=happy_test_user_input_short,
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code == 404
    assert response.json().get("message") == "Database cound not find given resource"
    service.save_user_input.assert_called_once_with(
        user_input="What are you?", conversation_id=1, user_id=1
    )
    client.app.dependency_overrides.clear()


def test_chat_streaming_save_bot_output_error(
    client, happy_test_user_input_short, valid_token
):
    """Function tests API response when there is an error within save_bot_output.
    Since function save_bot_output is inside StreamingResponse it can not riase an error and I can not let this error go to FastAPI exception handler since there is no wayt o change HTTP response. Otherwise I will get raise RuntimeError("Caught handled exception, but response already started.")

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)

        happy_test_user_input_short (UserInput): ficxture tyo store user input and chat histroy, successfully converted into Pydantic models
    """
    repo_mock = Mock()
    repo_mock.conversation_summary_presence.return_value = True
    repo_mock.chat_history.return_value = []
    repo_mock.save_bot_output.side_effect = DataBaseResourceNotFound()
    rag_chain = Mock()
    # rag_chain.stream.return_value = ServerSentEvent(event="token", data="answer")
    rag_chain.stream.return_value = [{"answer": "answer"}]

    # Keep the real service generator in the request path: it is responsible for
    # catching persistence failures after the streamed response has started.
    client.app.dependency_overrides[get_chat_repo] = lambda: repo_mock
    client.app.dependency_overrides[get_current_user] = lambda: UserDB(
        id=1, email="test@gmail.com", password_hash="test"
    )

    try:
        with patch.object(ChatService, "build_rag_chain", return_value=rag_chain):
            response = client.post(
                "v1/chat",
                json=happy_test_user_input_short,
                headers={"Authorization": f"Bearer {valid_token}"},
            )
    finally:
        client.app.dependency_overrides.clear()

    events = list(sseclient.SSEClient(response.iter_bytes()).events())
    assert (
        response.status_code == 200
    )  # ! Even when error occured , StreamingResponse has already started so HTTP response is 200. Error is visible in logs only
    assert len(events) == 1
    assert events[0].event == "token"
    assert events[0].data == "answer"
    repo_mock.save_bot_output.assert_called_once_with(
        output="answer", conversation_id=1, user_id=1
    )


#! Invalid token


def test_chat_invalid_token(client, invalid_token, happy_test_user_input_short):

    session = client.app.state.session_maker()
    user = Users(email="test@gmail.com", password_hash="test")
    session.add(user)
    session.commit()

    response = client.post(
        "v1/chat",
        json=happy_test_user_input_short,
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 401
