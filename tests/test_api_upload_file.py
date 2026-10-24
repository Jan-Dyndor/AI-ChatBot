from pathlib import Path
from unittest.mock import Mock

import pytest
from tenacity import wait_none

import backend.retry.retry_logs as retry_logs
from backend.api.schemas.pydantic_schemas import UserDB
from backend.dependencies.depends import (
    create_file_vector_storage,
    get_current_user,
    get_file_service,
)
from backend.exceptions.exc import FailedFileCleanUp, FileToLarge
from backend.service.file_service import FileService
from RAG.file_vector_repository import FileVectorStorage


@pytest.fixture
def uploaded_user() -> UserDB:
    return UserDB(id=7, email="upload@example.com", password_hash="hash")


@pytest.fixture
def upload_dependencies(client, uploaded_user):
    """Replace I/O dependencies, keeping the endpoint and BackgroundTasks real."""
    file_service = Mock(spec=FileService)
    file_service.save_file.return_value = Path("/tmp/stored-report.pdf")

    index_service = Mock()
    vector_store = Mock()
    vector_storage = FileVectorStorage(vector_store, index_service)

    client.app.dependency_overrides.update(
        {
            get_current_user: lambda: uploaded_user,
            get_file_service: lambda: file_service,
            create_file_vector_storage: lambda: vector_storage,
        }
    )
    yield file_service, index_service, vector_store
    client.app.dependency_overrides.pop(get_current_user, None)
    client.app.dependency_overrides.pop(get_file_service, None)
    client.app.dependency_overrides.pop(create_file_vector_storage, None)


def test_upload_file_saves_file_returns_sanitized_name_and_indexes_in_background(
    client, upload_dependencies
):
    file_service, index_service, vector_store = upload_dependencies
    chunks = [Mock()]
    index_service.load_and_split_pdf.return_value = chunks

    response = client.post(
        "/v1/file",
        files={"file": ("../../report.pdf", b"pdf-content", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == {"file_name": "report.pdf", "status": "UPLOADED"}
    file_service.validate_file_size.assert_called_once()
    file_service.save_file.assert_called_once()
    assert file_service.save_file.call_args.kwargs == {
        "file_name": "report.pdf",
        "user_id": 7,
    }
    file_service.save_file_metadata.assert_called_once_with(
        file_name="report.pdf",
        user_id=7,
        file_path=Path("/tmp/stored-report.pdf"),
    )
    # TestClient waits for FastAPI BackgroundTasks before returning the response.
    index_service.load_and_split_pdf.assert_called_once_with(
        file_path=Path("/tmp/stored-report.pdf"), user_id=7
    )
    vector_store.add_documents.assert_called_once_with(documents=chunks)


def test_upload_file_retries_background_indexing_until_success(client, upload_dependencies):
    _, index_service, vector_store = upload_dependencies
    chunks = [Mock()]
    index_service.load_and_split_pdf.side_effect = [
        ConnectionError("vector service temporarily unavailable"),
        ConnectionError("vector service temporarily unavailable"),
        chunks,
    ]

    response = client.post(
        "/v1/file",
        files={"file": ("report.pdf", b"pdf-content", "application/pdf")},
    )

    assert response.status_code == 200
    assert index_service.load_and_split_pdf.call_count == 3
    vector_store.add_documents.assert_called_once_with(documents=chunks)


def test_upload_file_logs_after_all_background_indexing_retries_fail(
    client, upload_dependencies, monkeypatch
):
    """The terminal Tenacity callback logs the failure after exactly 3 attempts."""
    _, index_service, vector_store = upload_dependencies
    index_service.load_and_split_pdf.side_effect = ConnectionError("vector unavailable")
    final_log = Mock()
    monkeypatch.setattr(retry_logs.logger, "opt", Mock(return_value=final_log))

    vector_storage = client.app.dependency_overrides[create_file_vector_storage]()
    monkeypatch.setattr(vector_storage.add_document.retry, "wait", wait_none())

    # TestClient propagates a BackgroundTask exception even though an ASGI server
    # has sent the HTTP response before it starts executing this task.
    with pytest.raises(ConnectionError, match="vector unavailable"):
        client.post(
            "/v1/file",
            files={"file": ("report.pdf", b"pdf-content", "application/pdf")},
        )

    assert index_service.load_and_split_pdf.call_count == 3
    vector_store.add_documents.assert_not_called()
    final_log.error.assert_called_once()
    assert "All retry attempts failed (3)" in final_log.error.call_args.args[0]


def test_upload_file_does_not_save_or_index_when_file_is_too_large(
    client, upload_dependencies
):
    file_service, index_service, vector_store = upload_dependencies
    file_service.validate_file_size.side_effect = FileToLarge(
        file_name="large.pdf", user_id=7, max_size=1
    )

    response = client.post(
        "/v1/file",
        files={"file": ("large.pdf", b"pdf-content", "application/pdf")},
    )

    assert response.status_code == 400
    file_service.save_file.assert_not_called()
    index_service.load_and_split_pdf.assert_not_called()
    vector_store.add_documents.assert_not_called()


def test_upload_file_returns_safe_error_when_cleanup_of_failed_save_fails(
    client, upload_dependencies
):
    file_service, index_service, vector_store = upload_dependencies
    file_service.save_file.side_effect = FailedFileCleanUp(Path("/tmp/partial.pdf"))

    response = client.post(
        "/v1/file",
        files={"file": ("report.pdf", b"pdf-content", "application/pdf")},
    )

    # FailedFileCleanUp is an AppExceptions subclass, so FastAPI's registered
    # handler converts it to the client-safe response rather than exposing a path.
    assert response.status_code == 500
    assert response.json() == {"message": "Issue occured while saving the file"}
    file_service.save_file_metadata.assert_not_called()
    index_service.load_and_split_pdf.assert_not_called()
    vector_store.add_documents.assert_not_called()
