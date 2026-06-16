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
    page_title="Register",
    page_icon="📝",
)

st.title("📝 Register")
st.caption("Create a new account")


# If user is already logged in, move to chatbot page
if "access_token" in st.session_state and st.session_state.access_token:
    st.switch_page("pages/chatbot_page.py")


with st.form("register_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    password_repeat = st.text_input("Repeat password", type="password")

    submitted = st.form_submit_button("Create account")

    if submitted:
        if not email or not password or not password_repeat:
            st.error("Please fill in all fields.")
        elif password != password_repeat:
            st.error("Passwords do not match.")
        else:
            with logger.contextualize(request_id=REQUEST_ID):
                try:
                    response = requests.post(
                        settings.api_create_user_url,
                        json={
                            "email": email,
                            "password": password,
                        },
                        headers={
                            "Request-ID": f"{REQUEST_ID}",
                        },
                        timeout=10,
                    )
                    logger.debug(f"User {email} registration request")
                    backend_request_id = response.headers.get("Request-ID")
                    if backend_request_id != REQUEST_ID:
                        logger.error(
                            f"Request IDs does not match. Check Logs. Frontend generated {REQUEST_ID} and backed gave back {backend_request_id}"
                        )

                    if response.status_code == 409:
                        st.error("User with this email already exists.")
                        logger.warning(
                            f"Register User Response: {response.status_code} User with this email {email} already exists"
                        )
                        st.stop()
                    elif response.status_code == 422:
                        error = response.json()
                        st.error(f"Invalid data provided {error}")
                        logger.warning(
                            f"Register User  {email} response with wrongly formated input data. Status code: {response.status_code} . Error: {error}"
                        )
                        st.stop()

                    response.raise_for_status()

                    st.success("Account created successfully. You can now log in.")
                    logger.debug(f"Successfull User registration {email}")

                except requests.RequestException:
                    st.error("Backend is unavailable. Check if FastAPI is running.")
                    logger.exception(
                        f"Exception occured while registering User {email}"
                    )

st.markdown("---")

if st.button("Back to login"):
    st.switch_page("pages/login_page.py")
