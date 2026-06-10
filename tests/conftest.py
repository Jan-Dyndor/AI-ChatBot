import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.schemas.pydantic_schemas import ChatMessage, UserInput
from backend.configuration.settings import get_settings
from backend.database.db import Base
from backend.database.models import Users
from backend.database.chat_repository import ChatRepository
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
        chat_history=[ChatMessage(role="assistant", content="What are you?")],
        model="llama3:8b",
        conversation_id=1,
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
        conversation_id=1,
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


# =========== DB Fixture for UNIT testing
@pytest.fixture()  # Create one DB and one engine but i am not sure if its correct to do so = iwont create meny Db nd meny engiens jeust one but hten i have to del all info from DB after each test or just at the beggingin of each

# Explainiton: for now i do not see better option to deal with tetsting functions without Request so withcout app gettign created since app creates my Db and i can use request.app.state to obtain session_maker and use that as DB connection but when teting just simple functions in Repositry or Seervice layrt thats not the cas so i think i have to create new DB for this
def create_db():
    """Function creates DB and returns engine

    Returns:
        _type_: SqlAlchemy engine
    """
    engine = create_engine(
        url="sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def session_maker(create_db):
    return sessionmaker(bind=create_db, autoflush=False, autocommit=False)


@pytest.fixture
def session(session_maker):
    db = session_maker()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def repo_service(session):
    return ChatRepository(session)


@pytest.fixture
def test_user_db() -> Users:
    """Function creates User object with ID = 1

    Returns:
        Users: SQLAlchemy object ready to be added to DB by session
    """
    return Users(id=1, email="test", password_hash="test_yet_not_hash")


# ============ FIXTURES FOR INTEGRATION tests with request from TestClient
# DB creation is in create_app function
@pytest.fixture
def test_env(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("API_URL", "test_url")
    monkeypatch.setenv("DB_URL", "sqlite:///:memory:")
    monkeypatch.setenv("API_CHAT_HISTORY", "test_history_url")
    monkeypatch.setenv("API_CREATE_CONVERSATION", "create_conversation_url_test")
    monkeypatch.setenv(
        "API_LATEST_CONVERSATIONS_IDS", "test_latest_conversations_ids_url"
    )

    get_settings.cache_clear()


@pytest.fixture
def client(
    test_env,
):
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app=app) as client:
        yield client

    get_settings.cache_clear()
