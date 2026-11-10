"""HTTP contract and persisted state for deleting an owned document."""

import os

import pytest

from backend.database.file_repository import FileRepository
from backend.database.models import Files, FileStatus, IndexingStatus, Users
from backend.exceptions.exc import DataBaseError


def _create_document(
    client,
    tmp_path,
    *,
    file_status=FileStatus.READY,
    index_status=IndexingStatus.SUCCESS,
):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"%PDF-1.4\nexample\n%%EOF")
    with client.app.state.session_maker() as session:
        user = Users(email="test@gmail.com", password_hash="hash")
        session.add(user)
        session.flush()
        document = Files(
            user_id=user.id,
            original_file_name="document.pdf",
            storage_path=str(path),
            file_sha="document-sha",
            file_status=file_status,
            index_status=index_status,
        )
        session.add(document)
        session.commit()
        return user.id, document.id, path


def _status(client, file_id):
    with client.app.state.session_maker() as session:
        document = session.get(Files, file_id)
        return None if document is None else document.file_status


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "index_status", [IndexingStatus.SUCCESS, IndexingStatus.FAILURE]
)
def test_delete_completed_index_removes_file_chunks_and_metadata(
    client, valid_token, tmp_path, index_status
):
    user_id, file_id, path = _create_document(
        client, tmp_path, index_status=index_status
    )
    vector_store = client.app.state.vector_store
    vector_store.get.return_value = {"ids": [f"{file_id}_0"]}

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert response.status_code == 204
    assert response.content == b""
    assert not path.exists()
    assert _status(client, file_id) is None
    vector_store.get.assert_called_once_with(
        where={"$and": [{"user_id": user_id}, {"file_id": file_id}]}, include=[]
    )
    vector_store.delete.assert_called_once_with(ids=[f"{file_id}_0"])
    retry = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))
    assert retry.status_code == 404
    vector_store.delete.assert_called_once_with(ids=[f"{file_id}_0"])


@pytest.mark.parametrize(
    "index_status", [IndexingStatus.PENDING, IndexingStatus.PROCESSING]
)
def test_delete_rejects_unfinished_index_without_touching_resources(
    client, valid_token, tmp_path, index_status
):
    _, file_id, path = _create_document(client, tmp_path, index_status=index_status)
    vector_store = client.app.state.vector_store

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert 400 <= response.status_code < 500
    assert path.exists()
    assert _status(client, file_id) == FileStatus.READY
    vector_store.get.assert_not_called()
    vector_store.delete.assert_not_called()


def test_delete_rejects_second_request_while_record_is_deleting(
    client, valid_token, tmp_path
):
    _, file_id, path = _create_document(
        client, tmp_path, file_status=FileStatus.DELETING
    )
    vector_store = client.app.state.vector_store

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert response.status_code == 409
    assert path.exists()
    assert _status(client, file_id) == FileStatus.DELETING
    vector_store.get.assert_not_called()


def test_delete_rejects_file_still_being_uploaded_even_if_index_is_terminal(
    client, valid_token, tmp_path
):
    _, file_id, path = _create_document(
        client, tmp_path, file_status=FileStatus.PROCESSING
    )

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert 400 <= response.status_code < 500
    assert path.exists()
    assert _status(client, file_id) == FileStatus.PROCESSING
    client.app.state.vector_store.get.assert_not_called()


def test_delete_succeeds_only_after_index_moves_to_terminal_state(
    client, valid_token, tmp_path
):
    _, file_id, path = _create_document(
        client, tmp_path, index_status=IndexingStatus.PROCESSING
    )
    vector_store = client.app.state.vector_store
    vector_store.get.return_value = {"ids": []}

    first = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))
    assert 400 <= first.status_code < 500
    assert path.exists()
    assert _status(client, file_id) == FileStatus.READY
    vector_store.get.assert_not_called()

    with client.app.state.session_maker() as session:
        session.get(Files, file_id).index_status = IndexingStatus.SUCCESS
        session.commit()

    second = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))
    assert second.status_code == 204
    assert not path.exists()
    assert _status(client, file_id) is None


def test_deleting_status_is_committed_before_external_cleanup(
    client, valid_token, tmp_path, monkeypatch
):
    _, file_id, path = _create_document(client, tmp_path)
    vector_store = client.app.state.vector_store
    observed = []
    original_remove = os.remove

    def inspect_during_remove(path):
        observed.append(("storage", _status(client, file_id), path.exists()))
        original_remove(path)

    def inspect_during_vector_lookup(**kwargs):
        observed.append(("vector", _status(client, file_id), path.exists()))
        return {"ids": []}

    monkeypatch.setattr(
        "backend.database.file_repository.os.remove", inspect_during_remove
    )
    vector_store.get.side_effect = inspect_during_vector_lookup

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert response.status_code == 204
    assert observed == [
        ("storage", FileStatus.DELETING, True),
        ("vector", FileStatus.DELETING, False),
    ]
    assert _status(client, file_id) is None


@pytest.mark.parametrize("failure_at", ["get", "delete"])
def test_vector_failure_keeps_deleting_record_for_future_cleanup(
    client, valid_token, tmp_path, failure_at
):
    _, file_id, path = _create_document(client, tmp_path)
    vector_store = client.app.state.vector_store
    vector_store.get.return_value = {"ids": [f"{file_id}_0"]}
    getattr(vector_store, failure_at).side_effect = RuntimeError("Chroma unavailable")

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert response.status_code == 500
    assert not path.exists()
    assert _status(client, file_id) == FileStatus.DELETING
    retry = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))
    assert retry.status_code == 409


def test_database_failure_keeps_deleting_record_after_storage_and_vector_cleanup(
    client, valid_token, tmp_path, monkeypatch
):
    _, file_id, path = _create_document(client, tmp_path)
    vector_store = client.app.state.vector_store
    vector_store.get.return_value = {"ids": [f"{file_id}_0"]}

    def fail_db_delete(self, file_id, user_id):
        raise DataBaseError()

    monkeypatch.setattr(FileRepository, "delete_file_from_db", fail_db_delete)

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert response.status_code == 500
    assert not path.exists()
    assert _status(client, file_id) == FileStatus.DELETING
    vector_store.delete.assert_called_once_with(ids=[f"{file_id}_0"])


def test_storage_failure_keeps_deleting_record_and_does_not_touch_chroma(
    client, valid_token, tmp_path, monkeypatch
):
    _, file_id, path = _create_document(client, tmp_path)
    vector_store = client.app.state.vector_store

    def fail_remove(_path):
        raise PermissionError("storage unavailable")

    monkeypatch.setattr("backend.database.file_repository.os.remove", fail_remove)

    response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))

    assert response.status_code == 500
    assert path.exists()
    assert _status(client, file_id) == FileStatus.DELETING
    vector_store.get.assert_not_called()


def test_delete_of_missing_or_other_users_file_does_not_touch_resources(
    client, valid_token, tmp_path
):
    with client.app.state.session_maker() as session:
        session.add(Users(email="test@gmail.com", password_hash="hash"))
        other = Users(email="other@example.com", password_hash="hash")
        session.add(other)
        session.flush()
        path = tmp_path / "other.pdf"
        path.write_bytes(b"other")
        document = Files(
            user_id=other.id,
            original_file_name="other.pdf",
            storage_path=str(path),
            file_sha="other-sha",
            file_status=FileStatus.READY,
            index_status=IndexingStatus.SUCCESS,
        )
        session.add(document)
        session.commit()
        other_file_id = document.id

    for file_id in (other_file_id, other_file_id + 1000):
        response = client.delete(f"/v1/files/{file_id}", headers=_headers(valid_token))
        assert response.status_code == 404

    assert path.exists()
    assert _status(client, other_file_id) == FileStatus.READY
    client.app.state.vector_store.get.assert_not_called()


def test_delete_requires_authentication(client):
    response = client.delete("/v1/files/1")
    assert response.status_code == 401
