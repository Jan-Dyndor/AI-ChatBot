"""Deletion claim and repeatable cleanup steps without HTTP."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from backend.database.db import Base
from backend.database.file_repository import FileRepository
from backend.database.models import Files, FileStatus, IndexingStatus, Users
from backend.exceptions.exc import DataBaseError, FileInDeletionProcess
from backend.service.file_service import FileService
from RAG.file_vector_repository import FileVectorStorage


def _create_document(session, path, index_status=IndexingStatus.SUCCESS):
    user = Users(email="delete@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    document = Files(
        user_id=user.id,
        original_file_name="document.pdf",
        storage_path=str(path),
        file_sha="delete-sha",
        file_status=FileStatus.READY,
        index_status=index_status,
    )
    session.add(document)
    session.commit()
    return user.id, document.id


def test_claim_can_change_ready_to_deleting_only_once(
    file_repository, session, tmp_path
):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"PDF")
    user_id, file_id = _create_document(session, path)

    claimed_path = file_repository.mark_file_to_delete_atomic_operation(
        user_id, file_id
    )

    assert claimed_path == str(path)
    session.expire_all()
    assert session.get(Files, file_id).file_status == FileStatus.DELETING
    with pytest.raises(FileInDeletionProcess):
        file_repository.mark_file_to_delete_atomic_operation(user_id, file_id)
    assert path.exists()


def test_two_concurrent_claims_have_only_one_winner(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'claims.db'}", connect_args={"timeout": 10}
    )
    Base.metadata.create_all(engine)
    make_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with make_session() as session:
        user_id, file_id = _create_document(session, tmp_path / "document.pdf")

    barrier = Barrier(2)

    def claim():
        with make_session() as session:
            barrier.wait(timeout=5)
            try:
                return FileRepository(session).mark_file_to_delete_atomic_operation(
                    user_id, file_id
                )
            except FileInDeletionProcess:
                return "already deleting"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(), range(2)))
        assert set(results) == {"already deleting", str(tmp_path / "document.pdf")}
        with make_session() as session:
            assert session.get(Files, file_id).file_status == FileStatus.DELETING
    finally:
        engine.dispose()


def test_failed_claim_commit_rolls_back_and_keeps_file_available(
    file_repository, session, tmp_path
):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"PDF")
    user_id, file_id = _create_document(session, path)

    def fail_commit(_session):
        raise SQLAlchemyError("commit interrupted")

    event.listen(session, "before_commit", fail_commit)
    try:
        with pytest.raises(DataBaseError):
            file_repository.mark_file_to_delete_atomic_operation(user_id, file_id)
    finally:
        event.remove(session, "before_commit", fail_commit)

    session.expire_all()
    assert session.get(Files, file_id).file_status == FileStatus.READY
    assert path.exists()


def test_storage_cleanup_tolerates_file_already_missing(
    file_repository, session, tmp_path
):
    path = tmp_path / "already-gone.pdf"
    user_id, file_id = _create_document(session, path)

    FileService(file_repository).prepare_to_del_file_from_db(user_id, file_id)

    session.expire_all()
    assert session.get(Files, file_id).file_status == FileStatus.DELETING


def test_vector_cleanup_tolerates_no_remaining_chunks():
    vector_store = Mock()
    vector_store.get.return_value = {"ids": []}
    storage = FileVectorStorage(vector_store, Mock())

    storage.delete_document(user_id=7, file_id=17)
    storage.delete_document(user_id=7, file_id=17)

    assert vector_store.get.call_count == 2
    vector_store.delete.assert_not_called()


def test_metadata_cleanup_tolerates_record_already_missing(file_repository):
    file_repository.delete_file_from_db(user_id=7, file_id=17)
    file_repository.delete_file_from_db(user_id=7, file_id=17)


def test_cleanup_steps_can_finish_after_file_was_removed(
    file_repository, session, tmp_path
):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"PDF")
    user_id, file_id = _create_document(session, path)
    service = FileService(file_repository)
    vector_store = Mock()
    vector_store.get.return_value = {"ids": [f"{file_id}_0"]}
    vector_storage = FileVectorStorage(vector_store, Mock())

    service.prepare_to_del_file_from_db(user_id, file_id)
    assert not path.exists()
    assert session.get(Files, file_id).file_status == FileStatus.DELETING

    # A future cleanup worker must resume here; the HTTP claim cannot run again.
    vector_storage.delete_document(user_id, file_id)
    service.delete_file_from_db(user_id, file_id)

    assert session.get(Files, file_id) is None
    vector_store.delete.assert_called_once_with(ids=[f"{file_id}_0"])
