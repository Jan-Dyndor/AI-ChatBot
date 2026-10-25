from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.api.router.v1 import get_file, get_files
from backend.api.schemas.pydantic_schemas import FilesResponse, UserDB
from backend.exceptions.exc import DataBaseResourceNotFound
from backend.service.file_service import FileService


@pytest.fixture
def user() -> UserDB:
    return UserDB(id=7, email="files@example.com", password_hash="hash")


def test_get_all_users_files_converts_repository_records_to_response_models():
    repository = Mock()
    repository.get_all_user_files.return_value = [
        SimpleNamespace(id=11, original_file_name="report.pdf"),
        SimpleNamespace(id=12, original_file_name="notes.pdf"),
    ]

    result = FileService(repository).get_all_users_files(user_id=7)

    assert result == [
        FilesResponse(id=11, original_file_name="report.pdf"),
        FilesResponse(id=12, original_file_name="notes.pdf"),
    ]
    repository.get_all_user_files.assert_called_once_with(user_id=7)


def test_get_all_users_files_preserves_not_found_error_for_empty_accounts():
    repository = Mock()
    repository.get_all_user_files.side_effect = DataBaseResourceNotFound()

    with pytest.raises(DataBaseResourceNotFound):
        FileService(repository).get_all_users_files(user_id=7)


def test_get_file_delegates_to_repository_with_owner_and_file_id():
    repository = Mock()
    repository.get_file.return_value = "/tmp/report.pdf"

    result = FileService(repository).get_file(user_id=7, file_id=11)

    assert result == "/tmp/report.pdf"
    repository.get_file.assert_called_once_with(user_id=7, file_id=11)


def test_get_files_handler_passes_authenticated_user_id_to_file_service(user):
    file_service = Mock(spec=FileService)
    file_service.get_all_users_files.return_value = [
        FilesResponse(id=11, original_file_name="report.pdf")
    ]

    result = get_files(user=user, file_service=file_service)

    assert result == [FilesResponse(id=11, original_file_name="report.pdf")]
    file_service.get_all_users_files.assert_called_once_with(7)


def test_get_file_handler_passes_authenticated_user_and_requested_file_id(user):
    file_service = Mock(spec=FileService)
    file_service.get_file.return_value = "/tmp/report.pdf"

    result = get_file(file_id=11, user=user, file_service=file_service)

    assert str(result) == "/tmp/report.pdf"
    file_service.get_file.assert_called_once_with(user_id=7, file_id=11)
