from pathlib import Path
from unittest.mock import Mock

import pytest
from tenacity import wait_none

from RAG.file_vector_repository import FileVectorStorage


def test_add_document_retries_three_times_then_adds_chunks(monkeypatch):
    vector_store = Mock()
    indexing_service = Mock()
    chunks = [Mock()]
    ids = ["chunk-1"]
    indexing_service.load_and_split_pdf.side_effect = [
        OSError("temporary read error"),
        OSError("temporary read error"),
        (chunks, ids),
    ]
    storage = FileVectorStorage(vector_store, indexing_service)
    monkeypatch.setattr(storage.add_document.retry, "wait", wait_none())
    storage.delete_document = Mock()

    storage.add_document(Path("/tmp/report.pdf"), user_id=7, file_db_id=17)

    assert indexing_service.load_and_split_pdf.call_count == 3
    indexing_service.load_and_split_pdf.assert_called_with(
        file_path=Path("/tmp/report.pdf"), user_id=7, file_db_id=17
    )
    vector_store.add_documents.assert_called_once_with(documents=chunks, ids=ids)
    assert storage.delete_document.call_count == 2


def test_add_document_reraises_after_three_failed_attempts(monkeypatch):
    vector_store = Mock()
    indexing_service = Mock()
    indexing_service.load_and_split_pdf.side_effect = ConnectionError("unavailable")
    storage = FileVectorStorage(vector_store, indexing_service)
    monkeypatch.setattr(storage.add_document.retry, "wait", wait_none())
    storage.delete_document = Mock()

    with pytest.raises(ConnectionError, match="unavailable"):
        storage.add_document(Path("/tmp/report.pdf"), user_id=7, file_db_id=17)

    assert indexing_service.load_and_split_pdf.call_count == 3
    vector_store.add_documents.assert_not_called()
    assert storage.delete_document.call_count == 3
    storage.delete_document.assert_called_with(user_id=7, file_id=17)
