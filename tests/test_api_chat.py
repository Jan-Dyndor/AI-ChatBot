from unittest.mock import patch

from backend.chat_bot.client import ChatBotClient
from backend.database.models import Conversations, Messages, Users


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
    test_user_db,
):

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
