import requests
import streamlit as st

from backend.configuration.logging_config import logger
from backend.configuration.settings import get_settings

settings = get_settings()


def init_session_state() -> None:
    if "disabled" not in st.session_state:
        st.session_state.disabled = False

    if "conversation_id" not in st.session_state:
        try:
            conversetion_id = requests.get(settings.api_url_create_conversation)
            conversetion_id.raise_for_status()
            conversetion_id_int = conversetion_id.json()
            st.session_state.conversation_id = conversetion_id_int

        except requests.RequestException as error:
            disable_conversation()
            logger.exception(error)
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Hello. Could not create new conversation - check the logs of application. Try to reload the page. Now your are unable to write.",
                }
            ]

    if "messages" not in st.session_state:
        st.session_state.messages = []
        try:
            chat_history = requests.get(
                f"http://localhost:8000/v1/chat_history?conversation_id={st.session_state.conversation_id}",
                timeout=120,
            )
            messages = chat_history.json()
            chat_history.raise_for_status()
            if messages:
                for message in chat_history.json():
                    st.session_state.messages.append(message)
            else:
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": "Hi! How can I help you today?",
                    }
                ]

        except requests.RequestException as e:
            logger.exception(e)
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Hi! I could not fetch data from our previous conversation. Issue occured (details in fastAPI server logs). New conversation has started. How can I help you today?",
                }
            ]  # TODO check if it really starts new conversetion or not


def render_sidebar() -> None:
    with st.sidebar:
        st.title("🤖 AI Chatbot")
        st.markdown("---")

        st.subheader("Settings")
        model_name = st.selectbox(
            "Model",
            options=["llama3:8b"],
            index=0,
        )

        st.markdown("---")

        if st.button("Clear chat"):
            st.session_state.clear()
            init_session_state()
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Chat cleared. How can I help you now?",
                }
            ]

            st.rerun()

        st.markdown("---")
        st.caption("MVP version - Streamlit UI + FastAPI backend")

    return model_name  # type: ignore


def render_chat_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def get_ai_response(
    user_input: str, model: str, chat_history: list[dict], conversation_id: int
):
    try:
        response = requests.post(
            settings.api_url_ai_chat,
            json={
                "input": user_input,
                "model": model,
                "chat_history": chat_history,
                "conversation_id": conversation_id,
            },
            timeout=120,
            stream=True,
        )
        if response.status_code == 422:
            response_json = response.json()
            logger.error(response.json())
            yield f"\n\n\n\n\n[ERROR] {response_json["detail"][0]["msg"]}"
            return
        response.raise_for_status()

        for chunk in response.iter_content(chunk_size=1024):
            yield chunk.decode("utf-8")

    except requests.RequestException as e:
        logger.exception(e)
        yield "\n\n\n\n\n[ERROR] Backend is unavailable or stream was interrupted."
        return


def disable_conversation():
    """Disable User from writing in chat window"""
    st.session_state.disabled = True


def enable_conversation():
    """Enable User from writing in chat window"""
    st.session_state.disabled = False


def main() -> None:
    init_session_state()
    model_name = render_sidebar()

    st.title("Conversational AI App")
    st.caption("Chat with your local LLM backend")

    render_chat_history()

    user_input = st.chat_input(
        "Write your message here...",
        disabled=st.session_state.disabled,
        on_submit=disable_conversation,
    )

    if user_input:
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                placeholder = st.empty()
                ai_response = ""
                for chunk in get_ai_response(
                    user_input, model_name, st.session_state.messages, st.session_state.conversation_id  # type: ignore
                ):
                    ai_response += chunk
                    placeholder.markdown(ai_response)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": ai_response,
            }
        )
        enable_conversation()
        st.rerun()


if __name__ == "__main__":
    main()
