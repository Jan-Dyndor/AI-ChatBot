from pathlib import Path
from unittest.mock import Mock

import pytest
from tenacity import wait_none

from RAG.file_vector_repository import FileVectorStorage


def test_add_document_retries_three_times_then_adds_chunks(monkeypatch):
    vector_store = Mock()
    indexing_service = Mock()
    chunks = [Mock()]
    indexing_service.load_and_split_pdf.side_effect = [
        OSError("temporary read error"),
        OSError("temporary read error"),
        chunks,
    ]
    storage = FileVectorStorage(vector_store, indexing_service)
    monkeypatch.setattr(storage.add_document.retry, "wait", wait_none())

    storage.add_document(Path("/tmp/report.pdf"), user_id=7)

    assert indexing_service.load_and_split_pdf.call_count == 3
    vector_store.add_documents.assert_called_once_with(documents=chunks)


def test_add_document_reraises_after_three_failed_attempts(monkeypatch):
    vector_store = Mock()
    indexing_service = Mock()
    indexing_service.load_and_split_pdf.side_effect = ConnectionError("unavailable")
    storage = FileVectorStorage(vector_store, indexing_service)
    monkeypatch.setattr(storage.add_document.retry, "wait", wait_none())

    with pytest.raises(ConnectionError, match="unavailable"):
        storage.add_document(Path("/tmp/report.pdf"), user_id=7)

    assert indexing_service.load_and_split_pdf.call_count == 3
    vector_store.add_documents.assert_not_called()
