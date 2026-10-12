import math
from uuid import uuid4

import requests
import streamlit as st
from loguru import logger

from backend.configuration.settings import get_settings

settings = get_settings()
MAX_FILE_SIZE_MB: float = round(settings.max_file_size_BYTES / (1024 * 1024), 2)
STREAMLIT_WIDGET_LIMIT_MB: int = max(
    1, math.ceil(settings.max_file_size_BYTES / (1024 * 1024))
)

st.set_page_config(page_title="Upload document", page_icon="📄")


def _request_headers(request_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {st.session_state.access_token}",
        "Request-ID": request_id,
    }


if "access_token" not in st.session_state or not st.session_state.access_token:
    st.warning("You need to log in first.")
    st.switch_page("pages/login_page.py")
    st.stop()


st.title("📄 Upload document")
st.caption(f"Upload one document to your account. Maximum size: {MAX_FILE_SIZE_MB} MB.")

if uploaded_file_name := st.session_state.pop("uploaded_file_name", None):
    st.success(f"File '{uploaded_file_name}' uploaded successfully.")

uploaded_file = st.file_uploader(
    label="Choose a document",
    accept_multiple_files=False,
    type=["pdf"],
    max_upload_size=STREAMLIT_WIDGET_LIMIT_MB,
)

if st.button("Upload", type="primary", disabled=uploaded_file is None):
    if uploaded_file is None:
        st.error("Choose a file before uploading.")
        st.stop()

    request_id = str(uuid4())

    with logger.contextualize(request_id=request_id):
        try:
            response = requests.post(
                settings.api_upload_file_url,
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "application/octet-stream",
                    )
                },
                headers=_request_headers(request_id),
                timeout=120,
            )

            response_request_id = response.headers.get("Request-ID")
            if response_request_id != request_id:
                logger.warning(
                    f"Request IDs do not match: frontend={request_id}, backend={response_request_id}"
                )

            if response.ok:
                file_data = response.json()
                file_name = file_data.get("file_name", uploaded_file.name)
                logger.info(f"File uploaded successfully: file_name={file_name}")
                st.session_state.uploaded_file_name = file_name
                st.rerun()

            try:
                error_message = response.json().get("message", response.text)
            except ValueError:
                error_message = response.text

            logger.error(
                f"File upload failed: status={response.status_code}, message={error_message}"
            )
            st.error(f"Upload failed ({response.status_code}): {error_message}")

        except requests.RequestException as error:
            logger.exception(f"Could not upload file: {error}")
            st.error("Backend is unavailable. Check if FastAPI is running.")

if st.button("Back to chat"):
    st.switch_page("pages/chatbot_page.py")
