from io import BytesIO
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from tenacity import wait_none

import backend.database.file_repository as file_repository_module
from backend.database.file_repository import FileRepository
from backend.database.models import Files, Users
from backend.exceptions.exc import (
    DataBaseFileError,
    DataBaseResourceNotFound,
    FailedFileCleanUp,
)


def upload_file(content: bytes = b"example") -> UploadFile:
    return UploadFile(filename="example.txt", file=BytesIO(content))


def test_create_file_storage_place_creates_user_directory(tmp_path, monkeypatch):
    fake_file = tmp_path / "src" / "backend" / "database" / "file_repository.py"
    monkeypatch.setattr(file_repository_module, "__file__", str(fake_file))

    path = FileRepository(Mock()).create_file_storage_place(7, "report.pdf", file_id=13)

    assert path.parent == tmp_path / "storage" / "7"
    assert path.name.endswith("_report.pdf")
    assert UUID(path.name.removesuffix("_report.pdf"))
    assert path.parent.is_dir()


def test_save_file_writes_content_to_given_path(file_repository, tmp_path):
    path = tmp_path / "storage" / "1" / "stored.txt"
    path.parent.mkdir(parents=True)

    result = file_repository.save_file(
        upload_file(b"file contents"), "original.txt", 1, file_id=13, file_path=path
    )

    assert result is None
    assert path.read_bytes() == b"file contents"
    assert file_repository.db.query(file_repository_module.Files).count() == 0


def test_save_file_raises_cleanup_error_when_destination_is_not_writable(
    file_repository, tmp_path
):
    # The parent path is a regular file, so opening the destination fails.
    # Simulate cleanup failing as well to exercise FailedFileCleanUp.
    invalid_parent = tmp_path / "not_a_directory"
    invalid_parent.write_bytes(b"not a directory")
    path = invalid_parent / "stored.txt"

    with patch.object(
        file_repository,
        "delete_file_from_storage",
        side_effect=PermissionError("cleanup failed"),
    ):
        with patch.object(
            file_repository, "mark_file_status_to_delte"
        ) as mark_for_deletion:
            with pytest.raises(FailedFileCleanUp):
                file_repository.save_file(
                    upload_file(), "example.txt", 3, file_id=13, file_path=path
                )

    mark_for_deletion.assert_called_once_with(file_id=13, user_id=3)
    assert file_repository.db.query(file_repository_module.Files).count() == 0


def test_update_file_metadata_rolls_back_three_times_when_database_fails(
    file_repository, session, tmp_path, monkeypatch
):
    path = tmp_path / "stored.txt"
    owner = Users(email="metadata-owner@example.com", password_hash="hash")
    session.add(owner)
    session.flush()
    document = Files(
        user_id=owner.id,
        original_file_name="example.txt",
        storage_path="TO BE SET",
        file_sha="sha-example",
    )
    session.add(document)
    session.commit()
    user_id, file_id = owner.id, document.id

    file_repository.db.commit = Mock(
        side_effect=SQLAlchemyError("database unavailable")
    )
    monkeypatch.setattr(file_repository.update_file_metadata.retry, "wait", wait_none())

    with patch.object(
        file_repository, "mark_file_status_to_delte"
    ) as mark_for_deletion:
        with patch.object(file_repository, "delete_file_from_db") as delete_metadata:
            with patch.object(
                file_repository.db, "rollback", wraps=file_repository.db.rollback
            ) as rollback:
                with pytest.raises(DataBaseFileError):
                    file_repository.update_file_metadata(
                        user_id=user_id,
                        file_path=path,
                        file_id=file_id,
                        file_name="example.txt",
                    )

    assert rollback.call_count == 3
    mark_for_deletion.assert_called_once_with(file_id=file_id, user_id=user_id)
    delete_metadata.assert_called_once_with(file_id=file_id, user_id=user_id)
    session.refresh(document)
    assert document.storage_path == "TO BE SET"


def test_update_file_metadata_rejects_missing_file(file_repository, tmp_path):
    path = tmp_path / "stored.txt"

    with pytest.raises(DataBaseResourceNotFound):
        file_repository.update_file_metadata(
            user_id=3, file_path=path, file_id=17, file_name="example.txt"
        )


def test_delete_file_from_storage_removes_file(tmp_path):
    path = tmp_path / "stored.txt"
    path.write_bytes(b"contents")

    FileRepository(Mock()).delete_file_from_storage(path)

    assert not path.exists()


def test_update_indexing_status_rejects_another_users_file(file_repository, session):
    owner = Users(email="file-owner@example.com", password_hash="hash")
    other_user = Users(email="other-user@example.com", password_hash="hash")
    session.add_all([owner, other_user])
    session.flush()

    document = Files(
        user_id=owner.id,
        original_file_name="private.pdf",
        storage_path="/tmp/private.pdf",
        file_sha="test-sha-private",
        file_sha="test-sha-private",
    )
    session.add(document)
    session.commit()

    with pytest.raises(DataBaseResourceNotFound):
        file_repository.update_file_idnexing_status(
            user_id=other_user.id,
            file_id=document.id,
            new_status="SUCCESS",
        )

    session.refresh(document)
    assert document.index_status == "PENDING"
