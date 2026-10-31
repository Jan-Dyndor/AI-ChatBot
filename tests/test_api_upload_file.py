from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.api.router import v1
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
    """Replace dependencies unrelated to enqueuing the Celery task."""
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


@pytest.fixture
def enqueue_indexing(monkeypatch):
    """Prevent the API test from connecting to the real Celery broker."""
    delay = Mock()
    monkeypatch.setattr(v1.index_and_save_file, "delay", delay)
    return delay


def test_upload_file_saves_file_and_enqueues_indexing_task(
    client, upload_dependencies, enqueue_indexing
):
    file_service, _, _ = upload_dependencies

    response = client.post(
        "/v1/file",
        files={"file": ("../../report.pdf", b"pdf-content", "application/pdf")},
    )

    assert response.status_code == 202
    assert response.json() == {
        "file_name": "report.pdf",
        "status": "Recived document for indexing",
    }
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
    enqueue_indexing.assert_called_once_with("/tmp/stored-report.pdf", 7)


def test_upload_file_does_not_save_or_index_when_file_is_too_large(
    client, upload_dependencies, enqueue_indexing
):
    file_service, _, _ = upload_dependencies
    file_service.validate_file_size.side_effect = FileToLarge(
        file_name="large.pdf", user_id=7, max_size=1
    )

    response = client.post(
        "/v1/file",
        files={"file": ("large.pdf", b"pdf-content", "application/pdf")},
    )

    assert response.status_code == 400
    file_service.save_file.assert_not_called()
    enqueue_indexing.assert_not_called()


def test_upload_file_returns_safe_error_when_cleanup_of_failed_save_fails(
    client, upload_dependencies, enqueue_indexing
):
    file_service, _, _ = upload_dependencies
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
    enqueue_indexing.assert_not_called()
