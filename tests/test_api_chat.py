from unittest.mock import Mock, patch

from backend.chat_bot.client import ChatBotClient
from backend.database.models import Conversations, Messages
from backend.dependencies.depends import get_chat_repo
from backend.exceptions.exc import DataBaseResourceNotFound


def test_chat_wrong_user_input(client, wrong_user_input_empty):
    response = client.post("v1/chat", json=wrong_user_input_empty)
    assert response.status_code == 422


def test_chat_wrong_user_input_long(client, wrong_user_input_too_long):
    response = client.post("v1/chat", json=wrong_user_input_too_long)
    assert response.status_code == 422


@patch.object(ChatBotClient, "stream_response")
def test_chat_streaming_happy(
    chatbot_mock,
    client,
    happy_test_user_input_short,
    happy_model_stream_response,
    model_stream_response,
    test_user_db,
):
    """Full happy apth of /chat endpint. Saving user and bot mess to DB

    Args:
        chatbot_mock (Mock): Mock of LLM response.

        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)

        happy_test_user_input_short (UserInput): ficxture tyo store user input and chat histroy, successfully converted into Pydantic models

        happy_model_stream_response (str): Generator that yields chunks of str as LLM response

        model_stream_response (str): LLM model response , whole message how it should look like

        test_user_db (Users): object instance of Users
    """

    chatbot_mock.side_effect = happy_model_stream_response

    db_session = client.app.state.session_maker()
    db_session.add(test_user_db)
    db_session.commit()

    conversation_example = Conversations(user_id=test_user_db.id)
    db_session.add(conversation_example)
    db_session.commit()

    response = client.post(
        "v1/chat?user_id=1", json=happy_test_user_input_short
    )  #! Temporarly user_id is part of URL later after AUTH module implementation it will be changed

    chunks = []
    for chunk in response.iter_text():
        chunks.append(chunk)

    full_response_txt = "".join(chunks)
    assert full_response_txt.strip() == model_stream_response
    chatbot_mock.assert_called_once()
    client.app.dependency_overrides.clear()

    # DB

    mess = db_session.query(Messages).all()

    assert mess[0].content == "What are you?"
    assert (
        mess[1].content.strip()
        == "I am powerfull AI! I am here to destroy you! ".strip()
    )


def test_chat_streaming_save_user_input_error(client, happy_test_user_input_short):
    """Function tests API response when there is an error within save_user_input_function

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)

        happy_test_user_input_short (UserInput): ficxture tyo store user input and chat histroy, successfully converted into Pydantic models
    """
    repo_mock = Mock()
    repo_mock.save_user_input.side_effect = DataBaseResourceNotFound()

    client.app.dependency_overrides[get_chat_repo] = lambda: repo_mock

    response = client.post("v1/chat?user_id=1", json=happy_test_user_input_short)

    assert response.status_code == 404
    assert response.json().get("message") == "Database cound not find given resource"
    client.app.dependency_overrides.clear()


def test_chat_streaming_save_bot_output_error(client, happy_test_user_input_short):
    """Function tests API response when there is an error within save_bot_output.
    Since function save_bot_output is inside StreamingResponse it can not riase an error and I can not let this error go to FastAPI exception handler since there is no wayt o change HTTP response. Otherwise I will get raise RuntimeError("Caught handled exception, but response already started.")

    Args:
        client (TestClient): TestClient from FastAPI. It invoked create_app function (creates DB, saves sessionmaker object in app.state, attaches middleware and router)

        happy_test_user_input_short (UserInput): ficxture tyo store user input and chat histroy, successfully converted into Pydantic models
    """
    repo_mock = Mock()
    repo_mock.save_bot_output.side_effect = DataBaseResourceNotFound()

    client.app.dependency_overrides[get_chat_repo] = lambda: repo_mock

    response = client.post("v1/chat?user_id=1", json=happy_test_user_input_short)

    assert (
        response.status_code == 200
    )  # ! Even when error occured , StreamingResponse has already started so HTTP response is 200. Error is visible in logs only
    client.app.dependency_overrides.clear()
