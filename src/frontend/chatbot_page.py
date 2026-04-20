import requests
import streamlit as st

API_URL = "http://0.0.0.0:8000/v1/chat"


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! How can I help you today?",
            }
        ]


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


def get_ai_response(user_input: str, model: str, chat_history: list[dict]):
    try:
        response = requests.post(
            API_URL,
            json={"input": user_input, "model": model, "chat_history": chat_history},
            timeout=120,
            stream=True,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error while connecting to backend: {e}"  # TODO
    # Silent UI bugs. If return will run -> for loop will never run and UI will not get error message. UI will get emnpty generator and therefore empty model response , so user will not know whats happening.
    # TODO What to do?
    # 1. Create backedn application error if somethig will go wrong and pass this here as structured error ( few approaches do it at mdoel responce level or at Fastapi level later when sending data, creconsider)
    # 2. raise Streamlit error but do not use return

    for chunk in response.iter_content(chunk_size=1024):
        yield chunk.decode("utf-8")


def main() -> None:
    init_session_state()
    model_name = render_sidebar()

    st.title("Conversational AI App")
    st.caption("Chat with your local LLM backend")

    render_chat_history()

    user_input = st.chat_input("Write your message here...")

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
                    user_input, model_name, st.session_state.messages  # type:ignore
                ):
                    ai_response += chunk
                    placeholder.markdown(ai_response)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": ai_response,
            }
        )


if __name__ == "__main__":
    main()
