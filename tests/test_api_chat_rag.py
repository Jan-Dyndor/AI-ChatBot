"""Comprehensive tests for the authenticated, streaming RAG chat endpoint.

The endpoint is tested with a fake ChatService so the tests do not require a
running Ollama server or a Chroma collection.  The service-level tests below
then verify the important RAG contract independently.
"""

from unittest.mock import Mock

import pytest
import sseclient
from sse_starlette import ServerSentEvent

import backend.service.chat_service as chat_service_module
from backend.api.schemas.pydantic_schemas import UserDB
from backend.dependencies.depends import (
    get_chat_service,
    get_current_user,
    get_thread_lock,
)
from backend.service.chat_service import ChatService


class RecordingLock:
    def __init__(self, acquired=False):
        self.acquired = acquired
        self.release_count = 0

    def acquire(self, blocking=False):
        return not self.acquired

    def release(self):
        self.acquired = False
        self.release_count += 1


class FakeChatService:
    def __init__(self, chunks=("answer ", "from RAG")):
        self.chunks = chunks
        self.calls = []

    def save_user_input(self, **kwargs):
        self.calls.append(("save_user_input", kwargs))

    def conversation_summary(self, **kwargs):
        self.calls.append(("conversation_summary", kwargs))

    def fetch_chat_history(self, **kwargs):
        self.calls.append(("fetch_chat_history", kwargs))
        return [{"role": "user", "content": "previous question"}]

    def thread_safe_rag_streaming_response(self, **kwargs):
        self.calls.append(("thread_safe_rag_streaming_response", kwargs))
        for chunk in self.chunks:
            yield ServerSentEvent(
                event="token",
                data=chunk,
            )
        kwargs["lock_object"].release()


@pytest.fixture
def chat_endpoint_overrides(client):
    service = FakeChatService()
    lock = RecordingLock()
    user = UserDB(id=7, email="chat@example.com", password_hash="unused")

    client.app.dependency_overrides[get_chat_service] = lambda: service
    client.app.dependency_overrides[get_current_user] = lambda: user
    client.app.dependency_overrides[get_thread_lock] = lambda: Mock(
        get_or_create_lock=lambda conversation_id: lock
    )
    yield service, lock
    client.app.dependency_overrides.clear()


def test_chat_streams_rag_answer_and_forwards_request_context(
    client, happy_test_user_input_short, chat_endpoint_overrides
):
    service, lock = chat_endpoint_overrides

    response = client.post("/v1/chat", json=happy_test_user_input_short)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert lock.release_count == 1

    response_client_generator = sseclient.SSEClient(response.iter_bytes())
    response_client = iter(response_client_generator.events())
    first_event = next(response_client)

    assert first_event.event == "token"
    assert first_event.data == "answer "

    second_event = next(response_client)
    assert second_event.event == "token"
    assert second_event.data == "from RAG"

    names = [name for name, _ in service.calls]
    assert names == [
        "conversation_summary",
        "fetch_chat_history",
        "save_user_input",
        "thread_safe_rag_streaming_response",
    ]
    stream_call = service.calls[-1][1]
    assert stream_call["question"] == "What are you?"
    assert stream_call["conversation_id"] == 1
    assert stream_call["user_id"] == 7
    assert stream_call["chat_history"] == [
        {"role": "user", "content": "previous question"}
    ]
    assert stream_call["temperature"] == 0
    assert stream_call["top_k"] == 1
    assert stream_call["top_p"] == 1
    assert stream_call["num_ctx"] == 512
    assert stream_call["num_predict"] == 1
    assert stream_call["repeat_penalty"] == 0.8
    assert stream_call["is_thinking"] is False


def test_chat_returns_conflict_without_writing_when_conversation_is_busy(
    client, happy_test_user_input_short
):
    service = Mock()
    lock = RecordingLock(acquired=True)
    client.app.dependency_overrides[get_chat_service] = lambda: service
    client.app.dependency_overrides[get_current_user] = lambda: UserDB(
        id=7, email="chat@example.com", password_hash="unused"
    )
    client.app.dependency_overrides[get_thread_lock] = lambda: Mock(
        get_or_create_lock=lambda conversation_id: lock
    )

    try:
        response = client.post("/v1/chat", json=happy_test_user_input_short)
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["message"] == "Conversation 1 already processing"
    service.save_user_input.assert_not_called()


def test_chat_releases_lock_when_pre_stream_work_fails(
    client, happy_test_user_input_short
):
    service = Mock()
    service.conversation_summary.side_effect = RuntimeError("database unavailable")
    lock = RecordingLock()
    client.app.dependency_overrides[get_chat_service] = lambda: service
    client.app.dependency_overrides[get_current_user] = lambda: UserDB(
        id=7, email="chat@example.com", password_hash="unused"
    )
    client.app.dependency_overrides[get_thread_lock] = lambda: Mock(
        get_or_create_lock=lambda conversation_id: lock
    )

    try:
        with pytest.raises(RuntimeError, match="database unavailable"):
            client.post("/v1/chat", json=happy_test_user_input_short)
    finally:
        client.app.dependency_overrides.clear()

    assert lock.release_count == 1
    service.fetch_chat_history.assert_not_called()


def test_chat_rejects_invalid_payload_before_service_calls(
    client, chat_endpoint_overrides
):
    service, _ = chat_endpoint_overrides
    response = client.post(
        "/v1/chat",
        json={
            "input": "",
            "model": "llama3:8b",
            "conversation_id": 1,
            "model_parameters": {},
        },
    )

    assert response.status_code == 422
    assert service.calls == []


def test_rag_pipeline_retrieves_only_the_requesting_users_documents(monkeypatch):
    llm = object()
    retriever = Mock()
    vector_storage = Mock()
    vector_storage.return_retiver.return_value = retriever
    db = Mock()
    bot = Mock()
    bot.get_llm.return_value = llm

    history_aware = object()
    answer_chain = object()
    rag_chain = Mock()
    rag_chain.stream.return_value = [
        {"answer": "grounded "},
        {"metadata": {"source": "manual.pdf"}},
        {"answer": "answer"},
    ]
    monkeypatch.setattr(
        chat_service_module,
        "create_history_aware_retriever",
        lambda actual_llm, actual_retriever, prompt: history_aware,
    )
    monkeypatch.setattr(
        chat_service_module,
        "create_stuff_documents_chain",
        lambda actual_llm, prompt: answer_chain,
    )
    monkeypatch.setattr(
        chat_service_module,
        "create_retrieval_chain",
        lambda actual_retriever, actual_answer_chain: rag_chain,
    )

    service = ChatService(
        db=db, chat_bot_client=bot, file_vector_storage=vector_storage
    )
    chunks = list(
        service.rag_streaming_response(
            model="llama3:8b",
            temperature=0.2,
            top_k=8,
            top_p=0.9,
            num_ctx=1024,
            num_predict=64,
            repeat_penalty=1.1,
            is_thinking=False,
            user_id=42,
            chat_history=[{"role": "user", "content": "old"}],
            question="What does the manual say?",
            conversation_id=3,
        )
    )

    bot.get_llm.assert_called_once_with(
        model="llama3:8b",
        temperature=0.2,
        top_k=8,
        top_p=0.9,
        num_ctx=1024,
        num_predict=64,
        repeat_penalty=1.1,
        is_thinking=False,
    )
    vector_storage.return_retiver.assert_called_once_with(
        serach_kwargs={"k": 3, "filter": {"user_id": 42}}
    )
    assert [(chunk.event, chunk.data) for chunk in chunks] == [
        ("token", "grounded "),
        ("token", "answer"),
    ]
    rag_chain.stream.assert_called_once_with(
        {
            "input": "What does the manual say?",
            "chat_history": [{"role": "user", "content": "old"}],
        }
    )
    db.save_bot_output.assert_called_once_with(
        output="grounded answer", conversation_id=3, user_id=42
    )
