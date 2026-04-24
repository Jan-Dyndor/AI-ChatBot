from unittest.mock import Mock, patch

from backend.chat_bot.client import ChatBot


@patch.object(ChatBot, "stream_response")
def test_chat_streaming(
    chatbot_instance,
    client,
    happy_test_user_input_short,
    happy_model_stream_response,
    model_stream_response,
):

    chatbot_instance.side_effect = happy_model_stream_response

    response = client.post("v1/chat", json=happy_test_user_input_short)

    chunks = []
    for chunk in response.iter_text():
        chunks.append(chunk)

    full_response_txt = "".join(chunks)
    assert full_response_txt.strip() == model_stream_response
