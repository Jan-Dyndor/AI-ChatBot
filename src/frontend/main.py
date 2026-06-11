import streamlit as st
from backend.configuration.logging_config import set_up_logging

set_up_logging()

if "access_token" in st.session_state and st.session_state.access_token:
    st.switch_page("pages/chatbot_page.py")
else:
    st.switch_page("pages/login_page.py")
