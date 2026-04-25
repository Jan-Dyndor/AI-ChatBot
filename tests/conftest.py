import time

import pytest
from fastapi.testclient import TestClient
from backend.configuration.settings import get_settings
from backend.api.schemas.pydantic_schemas import ChatMessage, UserInput
from backend.main import create_app


@pytest.fixture
def happy_test_user_input_short():
    return UserInput(
        input="What are you?",
        chat_history=[ChatMessage(role="assistant", content="What are you")],
        model="llama3:8b",
    ).model_dump()


@pytest.fixture
def happy_model_stream_response():
    """Function mock the behaviour or Streaming Response from AI Ollama model"""

    def streaming_generator(chat_history):
        for word in [
            "I",
            "am",
            "powerfull",
            "AI!",
            "I",
            "am",
            "here",
            "to",
            "destroy",
            "you!",
        ]:
            yield word + " "
            time.sleep(0.01)

    return streaming_generator


@pytest.fixture
def model_stream_response():
    return "I am powerfull AI! I am here to destroy you!".strip()


@pytest.fixture
def happy_test_user_input_long():
    return UserInput(
        input="What are you?",
        chat_history=[
            ChatMessage(role="user", content="What are you"),
            ChatMessage(
                role="assistant",
                content="I am powerfull AI! I am here to destroy you! ",
            ),
        ],
        model="llama3:8b",
    )


# Dependencies / clients Fixtures


@pytest.fixture
def test_env(monkeypatch):
    monkeypatch.setenv("API_URL", "test_url")


@pytest.fixture
def client(test_env):
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app=app) as client:
        yield client

    get_settings.cache_clear()
