from unittest.mock import patch

from backend.chat_bot.client import ChatBotClient
from backend.dependencies.depends import get_db


def test_chat_wrong_user_input(client, wrong_user_input_empty):
    response = client.post("v1/chat", json=wrong_user_input_empty)
    assert response.status_code == 422


def test_chat_wrong_user_input_long(client, wrong_user_input_too_long):
    response = client.post("v1/chat", json=wrong_user_input_too_long)
    assert response.status_code == 422


@patch.object(ChatBotClient, "stream_response")
def test_chat_streaming(
    chatbot_mock,
    client,
    happy_test_user_input_short,
    happy_model_stream_response,
    model_stream_response,
    # db_session_override,
):
    # client.app.dependency_overrides[get_db] = db_session_override
    chatbot_mock.side_effect = happy_model_stream_response

    response = client.post("v1/chat", json=happy_test_user_input_short)

    chunks = []
    for chunk in response.iter_text():
        chunks.append(chunk)

    full_response_txt = "".join(chunks)
    assert full_response_txt.strip() == model_stream_response
    chatbot_mock.assert_called_once()
    client.app.dependency_overrides.clear()


@patch.object(ChatBotClient, "stream_response")
def test_chat_streaming_with_dependecy_override(
    chatbot_mock,
    client,
    happy_test_user_input_short,
    # db_session_override,
    happy_model_stream_response,
):
    """Functioon will test streaming with dependency override. It does not go so deep like above function"""
    # client.app.dependency_overrides[get_db] = db_session_override
    chatbot_mock.side_effect = happy_model_stream_response

    result = client.post("/v1/chat", json=happy_test_user_input_short)
    chunks = []

    for chunk in result.iter_text():
        chunks.append(chunk)
        print(chunk)

    assert result.status_code == 200
    assert (
        "".join(chunks).strip()
        == "I am powerfull AI! I am here to destroy you! ".strip()
    )
    client.app.dependency_overrides.clear()
