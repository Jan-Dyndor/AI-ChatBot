"""Integration tests for authenticated document-listing and PDF-download endpoints."""

import pytest

from backend.database.models import Files, Users


def _authorization_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_user(session, email: str) -> Users:
    user = Users(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _create_file(session, user_id: int, name: str, path: str) -> Files:
    document = Files(
        user_id=user_id,
        original_file_name=name,
        storage_path=path,
    )
    session.add(document)
    session.flush()
    return document


def test_get_files_returns_only_authenticated_users_file_metadata(
    client, valid_token, tmp_path
):
    """The list response must not expose another user's files or storage paths."""
    session = client.app.state.session_maker()
    try:
        current_user = _create_user(session, "test@gmail.com")
        other_user = _create_user(session, "other@example.com")
        own_file = _create_file(
            session,
            current_user.id,
            "current-user.pdf",
            str(tmp_path / "current-user.pdf"),
        )
        _create_file(
            session,
            other_user.id,
            "other-user.pdf",
            str(tmp_path / "other-user.pdf"),
        )
        session.commit()

        response = client.get("/v1/files", headers=_authorization_header(valid_token))

        assert response.status_code == 200
        assert response.json() == [
            {"id": own_file.id, "original_file_name": "current-user.pdf"}
        ]
    finally:
        session.close()


def test_get_files_returns_404_when_authenticated_user_has_no_documents(
    client, valid_token
):
    session = client.app.state.session_maker()
    try:
        _create_user(session, "test@gmail.com")
        session.commit()

        response = client.get("/v1/files", headers=_authorization_header(valid_token))

        assert response.status_code == 404
        assert response.json() == {"message": "Database cound not find given resource"}
    finally:
        session.close()


def test_get_file_downloads_owned_pdf(client, valid_token, tmp_path):
    pdf_content = b"%PDF-1.4\nowned document\n%%EOF"
    pdf_path = tmp_path / "owned-document.pdf"
    pdf_path.write_bytes(pdf_content)

    session = client.app.state.session_maker()
    try:
        current_user = _create_user(session, "test@gmail.com")
        document = _create_file(
            session,
            current_user.id,
            "owned-document.pdf",
            str(pdf_path),
        )
        session.commit()

        response = client.get(
            f"/v1/files/{document.id}", headers=_authorization_header(valid_token)
        )

        assert response.status_code == 200
        assert response.content == pdf_content
        assert response.headers["content-type"].startswith("application/pdf")
    finally:
        session.close()


@pytest.mark.parametrize("requested_file_id", [9999, None])
def test_get_file_returns_404_for_missing_or_another_users_file(
    client, valid_token, tmp_path, requested_file_id
):
    """A valid JWT must never allow access to a document outside its owner."""
    other_pdf_path = tmp_path / "other-user.pdf"
    other_pdf_path.write_bytes(b"%PDF-1.4\nother user\n%%EOF")

    session = client.app.state.session_maker()
    try:
        _create_user(session, "test@gmail.com")
        other_user = _create_user(session, "other@example.com")
        other_document = _create_file(
            session,
            other_user.id,
            "other-user.pdf",
            str(other_pdf_path),
        )
        session.commit()

        file_id = other_document.id if requested_file_id is None else requested_file_id
        response = client.get(
            f"/v1/files/{file_id}", headers=_authorization_header(valid_token)
        )

        assert response.status_code == 404
        assert response.json() == {"message": "Database cound not find given resource"}
    finally:
        session.close()


@pytest.mark.parametrize("url", ["/v1/files", "/v1/files/1"])
def test_files_endpoints_require_authentication(client, url):
    response = client.get(url)

    assert response.status_code == 401
