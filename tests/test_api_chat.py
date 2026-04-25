from unittest.mock import patch

from backend.chat_bot.client import ChatBot


def test_chat_wrong_user_input(client, wrong_user_input_empty):
    response = client.post("v1/chat", json=wrong_user_input_empty)
    assert response.status_code == 422


def test_chat_wrong_user_input_long(client, wrong_user_input_too_long):
    response = client.post("v1/chat", json=wrong_user_input_too_long)
    assert response.status_code == 422


@patch.object(ChatBot, "stream_response")
def test_chat_streaming(
    chatbot_mock,
    client,
    happy_test_user_input_short,
    happy_model_stream_response,
    model_stream_response,
):

    chatbot_mock.side_effect = happy_model_stream_response

    response = client.post("v1/chat", json=happy_test_user_input_short)

    chunks = []
    for chunk in response.iter_text():
        chunks.append(chunk)

    full_response_txt = "".join(chunks)
    assert full_response_txt.strip() == model_stream_response
