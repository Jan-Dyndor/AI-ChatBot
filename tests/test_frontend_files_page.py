"""Visible file status and preview behavior on the Streamlit documents page."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from streamlit.testing.v1 import AppTest

PAGE_PATH = Path(__file__).resolve().parents[1] / "src/frontend/pages/files_page.py"


def _response(status_code, payload, request_id):
    response = requests.Response()
    response.status_code = status_code
    response.headers["Request-ID"] = request_id
    response._content = json.dumps(payload).encode()
    return response


def _file(file_status="READY", index_status="PENDING"):
    return {
        "id": 1,
        "original_file_name": "document.pdf",
        "file_status": file_status,
        "index_status": index_status,
    }


def _page():
    page = AppTest.from_file(str(PAGE_PATH))
    page.session_state["access_token"] = "test-token"
    return page


@pytest.mark.parametrize(
    ("file_status", "badge", "disabled"),
    [
        ("READY", ":green-badge[:material/check_circle: File ready]", False),
        ("PROCESSING", ":orange-badge[:material/sync: File processing]", True),
        ("DELETING", ":red-badge[:material/delete: Pending deletion]", True),
    ],
)
def test_file_status_controls_badge_and_preview_button(file_status, badge, disabled):
    page = _page()

    def fake_get(url, headers, timeout):
        return _response(200, [_file(file_status=file_status)], headers["Request-ID"])

    with patch("requests.get", side_effect=fake_get):
        page.run()

    assert not page.exception
    assert page.button[0].disabled is disabled
    status_badge = next(
        markdown for markdown in page.markdown if markdown.value == badge
    )
    if file_status == "DELETING":
        assert "error occurred" in status_badge.proto.help
        assert "marked for deletion" in status_badge.proto.help


@pytest.mark.parametrize(
    ("index_status", "badge"),
    [
        ("PENDING", ":gray-badge[:material/schedule: Indexing pending]"),
        ("PROCESSING", ":orange-badge[:material/sync: Indexing in progress]"),
        ("SUCCESS", ":green-badge[:material/check_circle: Indexing successful]"),
        ("FAILURE", ":red-badge[:material/error: Indexing failed]"),
    ],
)
def test_indexing_status_has_a_distinct_badge(index_status, badge):
    page = _page()

    def fake_get(url, headers, timeout):
        return _response(200, [_file(index_status=index_status)], headers["Request-ID"])

    with patch("requests.get", side_effect=fake_get):
        page.run()

    assert not page.exception
    assert any(markdown.value == badge for markdown in page.markdown)


def test_preview_shows_warning_and_clears_selection_if_status_changes():
    page = _page()
    message = "File document.pdf cannot be viewed while its status is DELETING."

    def fake_get(url, headers, timeout):
        if url.endswith("/1"):
            return _response(409, {"message": message}, headers["Request-ID"])
        return _response(200, [_file()], headers["Request-ID"])

    with patch("requests.get", side_effect=fake_get) as get:
        page.run()
        page.button[0].click().run()

    assert sum(call.args[0].endswith("/1") for call in get.call_args_list) == 1
    assert not page.exception
    assert [warning.value for warning in page.warning] == [message]
    assert "selected_file" not in page.session_state
    assert "selected_file_pdf" not in page.session_state


def test_delete_button_uses_its_file_id_and_refreshes_the_list():
    page = _page()
    files = [_file(), {**_file(), "id": 2, "original_file_name": "second.pdf"}]

    def fake_get(url, headers, timeout):
        return _response(200, files, headers["Request-ID"])

    def fake_delete(url, headers, timeout):
        assert url.endswith("/2")
        assert headers["Authorization"] == "Bearer test-token"
        files.pop()
        return _response(204, {}, headers["Request-ID"])

    with (
        patch("requests.get", side_effect=fake_get),
        patch("requests.delete", side_effect=fake_delete) as delete,
    ):
        page.run()
        page.button(key="delete-file-2").click().run()

    assert not page.exception
    assert delete.call_count == 1
    assert [success.value for success in page.success] == ["Deleted second.pdf."]
    assert any(button.key == "delete-file-1" for button in page.button)
    assert not any(button.key == "delete-file-2" for button in page.button)


def test_delete_failure_keeps_file_and_shows_backend_error():
    page = _page()

    def fake_get(url, headers, timeout):
        return _response(200, [_file()], headers["Request-ID"])

    def fake_delete(url, headers, timeout):
        return _response(500, {"message": "Deletion failed"}, headers["Request-ID"])

    with (
        patch("requests.get", side_effect=fake_get),
        patch("requests.delete", side_effect=fake_delete),
    ):
        page.run()
        page.button(key="delete-file-1").click().run()

    assert not page.exception
    assert any(button.key == "delete-file-1" for button in page.button)
    assert [error.value for error in page.error] == [
        "Could not delete this document (500): Deletion failed"
    ]
