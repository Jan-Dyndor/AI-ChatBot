from uuid import uuid4

import requests
import streamlit as st
from loguru import logger

from backend.configuration.settings import get_settings

settings = get_settings()


def init_session_state() -> None:
    """
    Streamlit session init

    - disabled in sesstion state - this parameter dictas if User is able to write new message
    - conversation_id - if absent we create new conversation if present system fetches messages from this conversation. If conversation was absent then system creates it and returns None (no previous conversations)

    """

    if "access_token" not in st.session_state or not st.session_state.access_token:
        st.warning("You need to log in first.")
        st.switch_page("pages/login_page.py")

    if "disabled" not in st.session_state:
        st.session_state.disabled = False

    if "conversation_id" not in st.session_state:
        REQUEST_ID: str = str(uuid4())
        with logger.contextualize(request_id=REQUEST_ID):

            try:
                response = requests.post(
                    "http://localhost:8000/v1/conversations",
                    headers={
                        "Authorization": f"Bearer {st.session_state.access_token}",
                        "Request-ID": f"{REQUEST_ID}",
                    },
                )
                response.raise_for_status()
                conversetion_id_int = response.json()
                logger.debug(f"Created conversation with ID {conversetion_id_int}")

                st.session_state.conversation_id = conversetion_id_int
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": "Hi! How can I help you today?",
                    }
                ]

            except requests.RequestException as error:
                disable_conversation()
                logger.exception(error)
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": "Hello. Could not create new conversation - check the logs of application. For now your are unable to write.",
                    }
                ]

    else:
        if "messages" not in st.session_state:
            st.session_state.messages = []
            REQUEST_ID: str = str(uuid4())
            with logger.contextualize(request_id=REQUEST_ID):
                try:
                    response = requests.get(
                        f"http://localhost:8000/v1/conversations/{st.session_state.conversation_id}/messages",
                        headers={
                            "Authorization": f"Bearer {st.session_state.access_token}",
                            "Request-ID": f"{REQUEST_ID}",
                        },
                        timeout=120,
                    )

                    logger.debug(
                        f"Fetched chat history for conversation ID {st.session_state.conversation_id} with status {response.status_code}"
                    )
                    response.raise_for_status()
                    messages = response.json()
                    if messages:
                        for message in messages:
                            st.session_state.messages.append(message)
                    else:
                        logger.debug(
                            f"Conversation with ID {st.session_state.conversation_id} has no old messages"
                        )
                        st.session_state.messages = [
                            {
                                "role": "assistant",
                                "content": "Hi! How can I help you today?",
                            }
                        ]

                except requests.RequestException as error:
                    logger.exception(
                        f" {error}. Could not fetch chat history for conversation {st.session_state.conversation_id}"
                    )
                    st.session_state.messages = [
                        {
                            "role": "assistant",
                            "content": "[ERROR] Hi! I could not fetch data from our previous conversation. Issue occured, check app logs",
                        }
                    ]


def get_conversation_history_ids() -> list[list] | int | None:
    """Function send GET request to DB and gives back default vanumber of latest user conversations IDs

    Returns:
        list[list] | int | None: When 200 response it gives back list of converssations IDs + title. If 404 - no conversetions yet found return 0 to inform user. If Error occured return None.
    """
    REQUEST_ID: str = str(uuid4())
    with logger.contextualize(request_id=REQUEST_ID):
        try:
            response = requests.get(
                "http://localhost:8000/v1/conversations",
                headers={
                    "Authorization": f"Bearer {st.session_state.access_token}",
                    "Request-ID": f"{REQUEST_ID}",
                },
                timeout=120,
            )

            if response.status_code == 404:
                return 0

            response.raise_for_status()

            if response.json() == []:
                return 0

            ids_summary_result = response.json()
            logger.debug(
                f"Latest conversations IDs response received: status={response.status_code}"
            )

            return ids_summary_result
        except requests.RequestException as error:
            logger.exception(
                f"{error}. Could not fetch latest conversations IDs from frontend"
            )
            return None


def render_sidebar():
    with st.sidebar:
        st.title("🤖 AI Chatbot")

        st.subheader("Settings")
        model_name = st.selectbox(
            "Model",
            options=["llama3:8b"],
            index=0,
        )

        temperature = st.slider(
            label="Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.1,
            key="temperature",
            help="Controls randomness. Lower = more focused, higher = more creative.",
        )

        top_k = st.slider(
            label="Top K",
            min_value=1,
            max_value=100,
            value=40,
            step=1,
            key="top_k",
            help="Limits token selection to the K most likely tokens.",
        )

        top_p = st.slider(
            label="Top P",
            min_value=0.0,
            max_value=1.0,
            value=0.9,
            step=0.05,
            key="top_p",
            help="Nucleus sampling. Lower = more focused, higher = more diverse.",
        )

        num_ctx = st.selectbox(
            label="Context length",
            options=[2048, 4096, 8192],
            index=1,
            key="num_ctx",
            help="How much text the model can keep in memory.",
        )

        num_predict = st.slider(
            label="Max response tokens",
            min_value=50,
            max_value=2000,
            value=300,
            step=50,
            key="num_predict",
            help="Maximum number of tokens the model is allowed to generate.",
        )

        repeat_penalty = st.slider(
            label="Repeat penalty",
            min_value=0.8,
            max_value=2.0,
            value=1.1,
            step=0.1,
            key="repeat_penalty",
            help="Penalizes repeated text. Higher values reduce repetition.",
        )

        if st.button("Start new chat"):
            logger.debug("Starting new chat")
            del st.session_state.conversation_id
            init_session_state()
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Chat cleared. How can I help you now?",
                }
            ]

            st.rerun()
        st.markdown("---")

        if st.button("Logout"):
            st.session_state.clear()
            st.switch_page("pages/login_page.py")
            print(st.session_state.conversation_id)

        conversations = get_conversation_history_ids()
        if conversations:
            st.subheader("Go back to previous conversations (Latest 10 by default)")
            for conversation_id_history in conversations:  # type: ignore
                if st.button(
                    label=str(conversation_id_history[1]),
                    key=int(conversation_id_history[0]),
                ):
                    del st.session_state.conversation_id
                    del st.session_state.messages
                    st.session_state.conversation_id = conversation_id_history[0]
                    init_session_state()
                    st.rerun()
        elif (
            conversations == 0
        ):  # DB returend 404 - User does not have previous conversations
            st.subheader("No previous conversations found")
        else:
            st.subheader(
                "Exception occured - could not download the chat history. Check logs"
            )

        st.caption("MVP version - Streamlit UI + FastAPI backend + DB Persistance")

    return model_name, temperature, top_k, top_p, num_ctx, num_predict, repeat_penalty


def render_chat_history() -> None:
    """Display chat messages"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def get_ai_response(
    user_input: str,
    model: str,
    chat_history: list[dict],
    conversation_id: int,
    temperature,
    top_k,
    top_p,
    num_ctx,
    num_predict,
    repeat_penalty,
):
    """


    Args:
        user_input (str): user new message
        model (str): LLM model
        chat_history (list[dict]): list of current chats
        conversation_id (int): ID of conversation

    Yields:
        str: LLM yields chunks
    """

    REQUEST_ID: str = str(uuid4())
    with logger.contextualize(request_id=REQUEST_ID):
        logger.debug("Sending user input to LLM")
        try:
            response = requests.post(
                "http://localhost:8000/v1/chat",
                json={
                    "input": user_input,
                    "model": model,
                    "chat_history": chat_history,
                    "conversation_id": conversation_id,
                    "model_parameters": {
                        "temperature": temperature,
                        "top_k": top_k,
                        "top_p": top_p,
                        "num_ctx": num_ctx,
                        "num_predict": num_predict,
                        "repeat_penalty": repeat_penalty,
                    },
                },
                headers={
                    "Authorization": f"Bearer {st.session_state.access_token}",
                    "Request-ID": f"{REQUEST_ID}",
                },
                timeout=120,
                stream=True,
            )

            logger.debug(f"LLM response recived with status {response.status_code}")

            if response.status_code == 422:
                response_json = response.json()
                logger.error(f"Input error by Pydantic: {response_json.get("message")}")
                yield f"\n\n\n\n\n[ERROR] {response_json.get("message")}"
                return
            elif response.status_code == 404:
                response_json = response.json()
                logger.error(response_json.get("message"))
                yield "\n\n\n\n\n[ERROR] DataBase error occured. Check logs"
                return
            elif response.status_code == 401:
                response_json = response.json()
                logger.error(response_json.get("message"))
                yield "\n\n\n\n\n[ERROR] Could not validate credentials. Token might be outdated. Login."
                return
            elif response.status_code == 502:
                response_json = response.json()
                logger.error(response_json.get("message"))
                yield "\n\n\n\n\n[ERROR] Ollama might not be working on your machine."
                return

            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=1024):
                yield chunk.decode("utf-8")

        except requests.RequestException as error:
            logger.exception(f"Could not fetch LLM response. {error}")
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
    model_name, temperature, top_k, top_p, num_ctx, num_predict, repeat_penalty = (
        render_sidebar()
    )

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
                    user_input,
                    model_name,  # type: ignore
                    st.session_state.messages,
                    st.session_state.conversation_id,  # type: ignore,
                    temperature,
                    top_k,
                    top_p,
                    num_ctx,
                    num_predict,
                    repeat_penalty,
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
