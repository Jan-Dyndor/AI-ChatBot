import time

import pytest
from fastapi.testclient import TestClient

from backend.api.schemas.pydantic_schemas import ChatMessage, UserInput
from backend.configuration.settings import get_settings
from backend.main import create_app


@pytest.fixture
def wrong_user_input_empty():
    return {
        "input": "",
        "model": "llama3:8b",
        "chat_history": [{"role": "assistant", "content": "example"}],
    }


@pytest.fixture
def wrong_user_input_too_long():
    return {
        "input": "example" * 3000,
        "model": "llama3:8b",
        "chat_history": [{"role": "assistant", "content": "example"}],
    }


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


# Dependencies / clients Fixtures / classs


@pytest.fixture
def FakeChatService_fixture():
    """Fixture returns callable class object that mimics the ChatService object"""

    class FakeChatService:
        def stream_response_from_client(self, model: str, chat_history: list):
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

    return FakeChatService


@pytest.fixture
def test_env(monkeypatch):
    monkeypatch.setenv("API_URL", "test_url")


@pytest.fixture
def client(
    test_env,
):
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app=app) as client:
        yield client

    get_settings.cache_clear()
