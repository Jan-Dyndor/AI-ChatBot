from uuid import uuid4

import requests
import streamlit as st
from loguru import logger

from backend.configuration.settings import get_settings

settings = get_settings()
REQUEST_ID: str = str(
    uuid4()
)  # Create Request ID, Streamlit will run this ptyhon script each time so fresh ID will occure


st.set_page_config(
    page_title="Login",
    page_icon="🔐",
)

st.title("🔐 Login")
st.caption("Log in to use the Conversational AI App")


# If user is already logged in, move to chatbot page
if "access_token" in st.session_state and st.session_state.access_token:
    st.switch_page("pages/chatbot_page.py")

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    submitted = st.form_submit_button("Log in")

    if submitted:
        if not email or not password:
            st.error("Please provide email and password.")
        else:
            with logger.contextualize(request_id=REQUEST_ID):
                try:
                    response = requests.post(
                        settings.api_token_url,
                        json={
                            "email": email,
                            "password": password,
                        },
                        headers={"Request-ID": f"{REQUEST_ID}"},
                        timeout=10,
                    )
                    logger.debug(f"User {email} login request")
                    data = response.json()

                    backend_request_id = response.headers.get("Request-ID")
                    if backend_request_id != REQUEST_ID:
                        logger.error(
                            f"Request IDs does not match. Check Logs. Frontend generated {REQUEST_ID} and backed gave back {backend_request_id}"
                        )

                    if response.status_code == 401:
                        logger.warning(
                            f"User {email} does not exists or porvided invalid password"
                        )
                        st.error("Invalid email or password.")
                        st.stop()
                    elif response.status_code == 422:
                        logger.warning(
                            f"User {email} entered wrongly formated input data - {data}"
                        )
                        st.error(f"Invalid data provided: {data}")
                        st.stop()

                    response.raise_for_status()

                    st.session_state.access_token = data["access_token"]
                    st.session_state.token_type = data.get("token_type", "bearer")

                    logger.debug(f"User {email} logged successfully")
                    st.success("Logged in successfully.")
                    st.switch_page("pages/chatbot_page.py")

                except requests.RequestException:
                    logger.exception(f"Exception occured while logging User {email}")
                    st.error("Backend is unavailable. Check if FastAPI is running.")


st.markdown("---")

if st.button("Create new account"):
    st.switch_page("pages/register_page.py")
