from backend.api.schemas.pydantic_schemas import ChatMessage, UserInput
from fastapi.testclient import TestClient
import pytest
from backend.main import app


@pytest.fixture
def happy_test_user_input_short():
    return UserInput(
        input="What are you?",
        chat_history=[ChatMessage(role="assistant", content="What are you")],
        model="llama3:8b",
    )


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
def client():
    with TestClient(app=app) as client:
        yield client
