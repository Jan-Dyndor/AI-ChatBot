"""Authenticated page showing documents uploaded by the current user."""

from uuid import uuid4

import requests
import streamlit as st
from loguru import logger

from backend.configuration.settings import get_settings

settings = get_settings()

st.set_page_config(page_title="My documents", page_icon="📚")


def _request_headers(request_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {st.session_state.access_token}",
        "Request-ID": request_id,
    }


def _get_error_message(response: requests.Response | None) -> str:
    """Return an error message without assuming the response is JSON."""
    if response is None:
        return "Backend returned no response."

    try:
        payload = response.json()
    except ValueError:
        return response.text[:500] or "Backend returned an empty error response."

    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("detail") or payload)

    return str(payload)


def _redirect_to_login_after_expired_session() -> None:
    """Clear expired credentials and explain the redirect on the login page."""
    st.session_state.clear()
    st.session_state.login_notice = "Your session has expired. Please log in again."
    st.switch_page("pages/login_page.py")


def _fetch_files() -> list[dict[str, object]] | None:
    """Return the current user's files; an empty account is represented by []."""
    request_id = str(uuid4())

    with logger.contextualize(request_id=request_id):
        try:
            response = requests.get(
                settings.api_files_url,
                headers=_request_headers(request_id),
                timeout=20,
            )

            response_request_id = response.headers.get("Request-ID")
            if response_request_id != request_id:
                logger.warning(
                    "Request IDs do not match: "
                    f"frontend={request_id}, backend={response_request_id}"
                )

            if response.status_code == 401:
                logger.warning("Session expired while fetching user files")
                _redirect_to_login_after_expired_session()

            # The current API deliberately returns 404 when this user has no files.
            if response.status_code == 404:
                return []

            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                logger.error(f"Files response has unexpected shape: {payload}")
                st.error("Could not load your documents: backend returned an invalid response.")
                return None

            files = [
                file
                for file in payload
                if isinstance(file, dict)
                and isinstance(file.get("id"), int)
                and isinstance(file.get("original_file_name"), str)
            ]
            if len(files) != len(payload):
                logger.error(f"Files response contains invalid records: {payload}")
                st.error("Could not load your documents: backend returned invalid file data.")
                return None

            logger.debug(f"Loaded {len(files)} files for the current user")
            return files

        except requests.HTTPError as error:
            response = error.response
            status_code = response.status_code if response is not None else "unknown"
            message = _get_error_message(response)
            logger.warning(
                f"Could not fetch user files: status={status_code}, message={message}"
            )
            st.error(f"Could not load your documents ({status_code}): {message}")
            return None

        except requests.RequestException as error:
            logger.exception(f"Could not fetch user files: {error}")
            st.error(
                "Could not connect to the backend. Check whether FastAPI is running."
            )
            return None


def _fetch_pdf(file_id: int) -> bytes | None:
    """Download one PDF owned by the current user."""
    request_id = str(uuid4())

    with logger.contextualize(request_id=request_id):
        try:
            response = requests.get(
                f"{settings.api_files_url.rstrip('/')}/{file_id}",
                headers=_request_headers(request_id),
                timeout=60,
            )

            response_request_id = response.headers.get("Request-ID")
            if response_request_id != request_id:
                logger.warning(
                    "Request IDs do not match: "
                    f"frontend={request_id}, backend={response_request_id}"
                )

            if response.status_code == 401:
                logger.warning(f"Session expired while fetching file {file_id}")
                _redirect_to_login_after_expired_session()

            response.raise_for_status()
            pdf_data = response.content
            if not pdf_data:
                logger.error(f"File endpoint returned an empty response: file_id={file_id}")
                st.error("Could not open this document: the file is empty.")
                return None

            content_type = response.headers.get("Content-Type", "")
            if not content_type.lower().startswith("application/pdf"):
                logger.error(
                    "File endpoint returned an unexpected content type: "
                    f"file_id={file_id}, content_type={content_type}"
                )
                st.error("Could not open this document: backend did not return a PDF.")
                return None

            logger.debug(f"Downloaded PDF for file_id={file_id}")
            return pdf_data

        except requests.HTTPError as error:
            response = error.response
            status_code = response.status_code if response is not None else "unknown"
            message = _get_error_message(response)
            logger.warning(
                "Could not fetch PDF: "
                f"file_id={file_id}, status={status_code}, message={message}"
            )
            st.error(f"Could not open this document ({status_code}): {message}")
            return None

        except requests.RequestException as error:
            logger.exception(f"Could not fetch PDF for file_id={file_id}: {error}")
            st.error(
                "Could not connect to the backend. Check whether FastAPI is running."
            )
            return None


if "access_token" not in st.session_state or not st.session_state.access_token:
    st.warning("You need to log in first.")
    st.switch_page("pages/login_page.py")
    st.stop()


st.title("📚 My documents")
st.caption("Documents uploaded to your account")

files = _fetch_files()

if files == []:
    st.session_state.pop("selected_file", None)
    st.session_state.pop("selected_file_pdf", None)
    st.info("You have not uploaded any documents yet.")
    if st.button("Upload a document", type="primary"):
        st.switch_page("pages/upload_page.py")
elif files:
    st.caption(f"{len(files)} document{'s' if len(files) != 1 else ''}")
    available_file_ids = {file["id"] for file in files}
    selected_file = st.session_state.get("selected_file")
    if (
        not isinstance(selected_file, dict)
        or selected_file.get("id") not in available_file_ids
    ):
        st.session_state.pop("selected_file", None)
        st.session_state.pop("selected_file_pdf", None)

    for file in files:
        with st.container(border=True):
            name_column, action_column = st.columns([7, 3])
            name_column.markdown(f"#### 📄 {file['original_file_name']}")
            name_column.caption(f"Document ID: {file['id']}")
            if action_column.button("Open PDF", key=f"open-file-{file['id']}"):
                st.session_state.selected_file = {
                    "id": file["id"],
                    "name": file["original_file_name"],
                }
                st.session_state.pop("selected_file_pdf", None)

    selected_file = st.session_state.get("selected_file")
    if isinstance(selected_file, dict):
        selected_file_id = selected_file.get("id")
        selected_file_name = selected_file.get("name")
        if isinstance(selected_file_id, int) and isinstance(selected_file_name, str):
            st.subheader(f"Preview: {selected_file_name}")
            cached_pdf = st.session_state.get("selected_file_pdf")
            if (
                not isinstance(cached_pdf, dict)
                or cached_pdf.get("file_id") != selected_file_id
                or not isinstance(cached_pdf.get("data"), bytes)
            ):
                with st.spinner("Loading PDF..."):
                    pdf_data = _fetch_pdf(selected_file_id)
                if pdf_data is not None:
                    st.session_state.selected_file_pdf = {
                        "file_id": selected_file_id,
                        "data": pdf_data,
                    }
                    cached_pdf = st.session_state.selected_file_pdf

            if isinstance(cached_pdf, dict) and isinstance(cached_pdf.get("data"), bytes):
                st.pdf(
                    cached_pdf["data"],
                    height=800,
                    key=f"file-preview-{selected_file_id}",
                )

if st.button("Back to chat"):
    st.switch_page("pages/chatbot_page.py")
