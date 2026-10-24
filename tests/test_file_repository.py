from io import BytesIO
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from tenacity import wait_none

import backend.database.file_repository as file_repository_module
from backend.database.file_repository import FileRepository
from backend.exceptions.exc import DataBaseFileError, FailedFileCleanUp


def upload_file(content: bytes = b"example") -> UploadFile:
    return UploadFile(filename="example.txt", file=BytesIO(content))


def test_create_file_storage_place_creates_user_directory(tmp_path, monkeypatch):
    fake_file = tmp_path / "src" / "backend" / "database" / "file_repository.py"
    monkeypatch.setattr(file_repository_module, "__file__", str(fake_file))

    path = FileRepository(Mock()).create_file_storage_place(7, "report.pdf")

    assert path.parent == tmp_path / "storage" / "7"
    assert path.name.endswith("_report.pdf")
    assert UUID(path.name.removesuffix("_report.pdf"))
    assert path.parent.is_dir()


def test_save_file_saves_content_and_metadata(file_repository, tmp_path):
    path = tmp_path / "storage" / "1" / "stored.txt"
    path.parent.mkdir(parents=True)

    with patch.object(file_repository, "create_file_storage_place", return_value=path):
        result = file_repository.save_file(
            upload_file(b"file contents"), "original.txt", 1
        )

    assert result == path
    assert path.read_bytes() == b"file contents"
    assert file_repository.db.query(file_repository_module.Files).count() == 0


def test_save_file_raises_cleanup_error_when_destination_is_not_writable(
    file_repository, tmp_path
):
    # The parent path is a regular file, so opening ``stored.txt`` below it
    # fails through the real filesystem. No ``open`` mock is needed.
    invalid_parent = tmp_path / "not_a_directory"
    invalid_parent.write_bytes(b"not a directory")
    path = invalid_parent / "stored.txt"

    with patch.object(file_repository, "create_file_storage_place", return_value=path):
        with pytest.raises(FailedFileCleanUp):
            file_repository.save_file(upload_file(), "example.txt", 3)

    assert file_repository.db.query(file_repository_module.Files).count() == 0


def test_save_file_metadata_rolls_back_three_times_when_database_fails(
    file_repository, tmp_path, monkeypatch
):
    path = tmp_path / "stored.txt"
    file_repository.db.commit = Mock(
        side_effect=SQLAlchemyError("database unavailable")
    )
    monkeypatch.setattr(file_repository.save_file_metadata.retry, "wait", wait_none())

    with patch.object(file_repository, "create_file_storage_place", return_value=path):
        with patch.object(
            file_repository.db, "rollback", wraps=file_repository.db.rollback
        ) as rollback:
            with pytest.raises(DataBaseFileError):
                file_repository.save_file_metadata("example.txt", 3, path)

    # Tenacity performs three total attempts, therefore each failed commit is rolled back.
    assert rollback.call_count == 3
    assert file_repository.db.query(file_repository_module.Files).count() == 0


def test_save_file_metadata_raises_database_error_after_retries(
    file_repository, tmp_path, monkeypatch
):
    path = tmp_path / "stored.txt"
    file_repository.db.commit = Mock(
        side_effect=SQLAlchemyError("database unavailable")
    )
    monkeypatch.setattr(file_repository.save_file_metadata.retry, "wait", wait_none())

    with pytest.raises(DataBaseFileError):
        file_repository.save_file_metadata("example.txt", 3, path)


def test_delete_file_from_storage_removes_file(tmp_path):
    path = tmp_path / "stored.txt"
    path.write_bytes(b"contents")

    FileRepository(Mock()).delete_file_from_storage(path)

    assert not path.exists()
