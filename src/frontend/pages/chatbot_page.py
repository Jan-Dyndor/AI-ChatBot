from uuid import uuid4

import requests
import sseclient
import streamlit as st
from loguru import logger

from backend.configuration.settings import get_settings
from frontend.frontend_exceptions.frontend_exceptions import (
    ChatStreamError,
    ConversaionInUse,
    DBError,
    InvalidCredentials,
    NetworkError,
    OllamaConnectionError,
    PydanticValidationError,
    UnknownError,
)

settings = get_settings()


def redirect_to_login_after_expired_session() -> None:
    """Clear expired credentials and send the user to the login page."""
    st.session_state.clear()
    st.session_state.login_notice = "Your session has expired. Please log in again."
    st.switch_page("pages/login_page.py")


def block_chat_after_initialization_error(user_message: str) -> None:
    """Persist an initialization error and prevent sending chat messages."""
    st.session_state.disabled = True
    st.session_state.messages = []
    st.session_state.initialization_error = user_message
    st.session_state.initialization_failed = True
    st.session_state.initialization_error_toast = True


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

    # Do not retry a failed request on every Streamlit rerun. The user can retry
    # explicitly with the "Start new chat" button.
    if st.session_state.get("initialization_failed", False):
        return

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
                    timeout=120,
                )
                response.raise_for_status()
                conversetion_id_int = response.json()
                logger.debug(f"Created conversation with ID {conversetion_id_int}")

                st.session_state.conversation_id = conversetion_id_int
                st.session_state.pop("initialization_error", None)
                st.session_state.pop("initialization_failed", None)
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": "Hi! How can I help you today?",
                    }
                ]
            except requests.HTTPError as error:
                response_error = error.response
                message = get_error_message(response_error)
                status_code = (
                    response_error.status_code
                    if response_error is not None
                    else "unknown"
                )
                if status_code == 401:
                    logger.warning("Session expired while creating a conversation")
                    redirect_to_login_after_expired_session()
                logger.exception(
                    f"Issue occured while creating new conversation - {message} with status {status_code}"
                )
                block_chat_after_initialization_error(
                    "Could not create a new conversation. Start a new chat to try again."
                )

            except requests.RequestException as error:
                logger.exception(
                    f"Request failed while tring to create conversation {error}"
                )
                block_chat_after_initialization_error(
                    "Could not connect to the backend. Start a new chat to try again."
                )

            except Exception as ex:
                logger.exception(
                    f"Unknon exception occured while creating conversation {ex}"
                )
                block_chat_after_initialization_error(
                    "An unexpected error occurred while creating a conversation. "
                    "Start a new chat to try again."
                )

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
                except requests.HTTPError as error:
                    if error.response is not None and error.response.status_code == 401:
                        logger.warning(
                            "Session expired while loading conversation history"
                        )
                        redirect_to_login_after_expired_session()
                    logger.exception(
                        f" {error}. Could not fetch chat history for conversation {st.session_state.conversation_id}"
                    )
                    block_chat_after_initialization_error(
                        "Could not load this conversation. Start a new chat to try again."
                    )

                except requests.RequestException as error:
                    logger.exception(
                        f" {error}. Could not fetch chat history for conversation {st.session_state.conversation_id}"
                    )
                    block_chat_after_initialization_error(
                        "Could not connect to the backend. Start a new chat to try again."
                    )
                except Exception as error:
                    logger.exception(
                        f"Unknon exception occured while creating conversation {error}"
                    )
                    block_chat_after_initialization_error(
                        "An unexpected error occurred while loading the conversation. "
                        "Start a new chat to try again."
                    )


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

            if response.status_code == 401:
                logger.warning("Session expired while fetching conversation list")
                redirect_to_login_after_expired_session()

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


def _conversation_ids(conversations: list[list] | int | None) -> list[int]:
    """Return just the conversation IDs from the latest-conversations response."""
    if not isinstance(conversations, list):
        return []

    return [int(conversation[0]) for conversation in conversations]


def refresh_conversation_history_ids() -> list[list] | int | None:
    """Fetch and cache latest conversation metadata in Streamlit session state."""
    conversations = get_conversation_history_ids()
    st.session_state.conversations_list_ids = _conversation_ids(conversations)
    st.session_state.conversations_history = conversations
    st.session_state.conversations_history_stale = conversations is None
    return conversations


def get_cached_conversation_history_ids() -> list[list] | int | None:
    """Return cached latest conversations unless a chat action made them stale."""
    if "conversations_history" not in st.session_state or st.session_state.get(
        "conversations_history_stale", False
    ):
        return refresh_conversation_history_ids()

    return st.session_state.conversations_history


def mark_conversation_history_stale() -> None:
    """Mark cached conversations stale so the next render refreshes them once."""
    st.session_state.conversations_history_stale = True


def get_available_models() -> list[str]:
    """Fetch available Ollama models once per Streamlit session."""
    if "available_models" in st.session_state:
        return st.session_state.available_models

    REQUEST_ID: str = str(uuid4())
    fallback_models = ["llama3:8b"]

    with logger.contextualize(request_id=REQUEST_ID):
        try:
            response = requests.get(
                "http://localhost:8000/v1/models",
                headers={
                    "Authorization": f"Bearer {st.session_state.access_token}",
                    "Request-ID": f"{REQUEST_ID}",
                },
                timeout=120,
            )
            if response.status_code == 401:
                logger.warning("Session expired while fetching available models")
                redirect_to_login_after_expired_session()
            response.raise_for_status()

            models = [
                model["model"]
                for model in response.json().get("models", [])
                if model.get("model")
            ]
            st.session_state.available_models = models or fallback_models
            logger.debug(
                f"Fetched available models: {st.session_state.available_models}"
            )

        except requests.RequestException as error:
            logger.exception(f"Could not fetch available models. {error}")
            st.session_state.available_models = fallback_models

    return st.session_state.available_models


def render_sidebar():
    with st.sidebar:
        st.title("🤖 AI Chatbot")

        st.subheader("Settings")
        available_models = get_available_models()
        model_name = st.selectbox(
            "Model",
            options=available_models,
            index=0,
            key="model_name",
        )

        reasoning = st.selectbox(
            "LLM reasoning",
            options=[False, True],
            help=(
                "Allows compatible models to think before writing the final answer. Useful for complex coding, "
                "math, planning, or analysis tasks. It can make responses slower and may use part of the "
                "Max response tokens budget. Some models ignore this option."
            ),
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
            help=(
                "Maximum tokens the model may generate. If Reasoning mode is enabled, internal reasoning "
                "can use part of this budget before the final answer appears."
            ),
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
            st.session_state.pop("conversation_id", None)
            st.session_state.pop("messages", None)
            st.session_state.pop("initialization_error", None)
            st.session_state.pop("initialization_failed", None)
            st.session_state.pop("initialization_error_toast", None)
            enable_conversation()
            init_session_state()
            mark_conversation_history_stale()
            st.rerun()

        if st.button("Upload document"):
            st.switch_page("pages/upload_page.py")

        st.markdown("---")

        if st.button("Logout"):
            st.session_state.clear()
            st.switch_page("pages/login_page.py")

        conversations = get_cached_conversation_history_ids()
        if conversations:
            st.subheader("Go back to previous conversations (Latest 10 by default)")
            for conversation_id_history in conversations:  # type: ignore
                if st.button(
                    label=str(conversation_id_history[1]),
                    key=int(conversation_id_history[0]),
                ):
                    st.session_state.pop("conversation_id", None)
                    st.session_state.pop("messages", None)
                    st.session_state.pop("initialization_error", None)
                    st.session_state.pop("initialization_failed", None)
                    st.session_state.pop("initialization_error_toast", None)
                    enable_conversation()
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

    return (
        model_name,
        temperature,
        top_k,
        top_p,
        num_ctx,
        num_predict,
        repeat_penalty,
        reasoning,
    )


def render_chat_history() -> None:
    """Display chat messages"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def get_error_message(response: requests.Response | None) -> str:
    """Extract a safe diagnostic message from an error response."""
    if response is None:
        return "Backend returned no response."

    try:
        payload = response.json()
    except ValueError:
        return response.text[:500] or "Backend returned an empty error response."

    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("detail") or payload)

    return str(payload)


def get_ai_response(
    user_input: str,
    model: str,
    conversation_id: int,
    temperature,
    top_k,
    top_p,
    num_ctx,
    num_predict,
    repeat_penalty,
    reasoning: bool,
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
        response = None
        try:
            response = requests.post(
                "http://localhost:8000/v1/chat",
                json={
                    "input": user_input,
                    "model": model,
                    "conversation_id": conversation_id,
                    "model_parameters": {
                        "temperature": temperature,
                        "top_k": top_k,
                        "top_p": top_p,
                        "num_ctx": num_ctx,
                        "num_predict": num_predict,
                        "repeat_penalty": repeat_penalty,
                        "is_thinking": reasoning,
                    },
                },
                headers={
                    "Authorization": f"Bearer {st.session_state.access_token}",
                    "Request-ID": f"{REQUEST_ID}",
                },
                timeout=120,
                stream=True,
            )

            try:
                logger.debug(f"LLM response recived with status {response.status_code}")

                if response.status_code == 422:
                    response_json_message = get_error_message(response)
                    logger.warning(response_json_message)
                    raise PydanticValidationError(response_json_message)
                elif response.status_code == 404:
                    response_json_message = get_error_message(response)
                    logger.warning(response_json_message)
                    raise DBError(response_json_message)
                elif response.status_code == 401:
                    response_json_message = get_error_message(response)
                    logger.warning(response_json_message)
                    raise InvalidCredentials(response_json_message)
                elif response.status_code == 502:
                    response_json_message = get_error_message(response)
                    logger.warning(response_json_message)
                    raise OllamaConnectionError(response_json_message)
                elif response.status_code == 409:
                    response_json_message = get_error_message(response)
                    logger.warning(response_json_message)
                    raise ConversaionInUse(
                        message=response_json_message,
                        user_message="Conversation process request. You can not send multiple requests to the same conversation in the same time.",
                    )

                response.raise_for_status()

                client = sseclient.SSEClient(response)  # type: ignore
                for event in client.events():
                    if event.event == "token":
                        yield event.data
                    elif event.event == "error":
                        logger.error(event.data)
                        raise ChatStreamError(event.data)
                    else:
                        logger.warning(f"Unknown SSE event: {event.event}")

            except requests.HTTPError as error:

                response = error.response
                status_code = (
                    response.status_code if response is not None else "unknown"
                )
                message = get_error_message(response)
                logger.warning(
                    f"Backend HTTP error: status={status_code}, message={message}"
                )
                raise UnknownError(
                    message=message,
                    user_message="An unexpected backend error occurred. Please try again.",
                ) from error

        except requests.RequestException as error:
            logger.exception(error)
            raise NetworkError(
                message=str(error),
                user_message="Could not conenct to backend service",
            ) from error

        finally:
            if response is not None:
                response.close()


def disable_conversation():
    """Disable User from writing in chat window"""
    st.session_state.disabled = True


def enable_conversation():
    """Enable User from writing in chat window"""
    st.session_state.disabled = False


def main() -> None:
    init_session_state()
    (
        model_name,
        temperature,
        top_k,
        top_p,
        num_ctx,
        num_predict,
        repeat_penalty,
        reasoning,
    ) = render_sidebar()

    st.title("Conversational RAG AI App")
    st.caption("Chat with your local docs with help of LLM on backend")

    if initialization_error := st.session_state.get("initialization_error"):
        if st.session_state.pop("initialization_error_toast", False):
            st.toast(initialization_error, icon="⚠️")
        st.error(initialization_error)

    render_chat_history()

    if error := st.session_state.pop("chat_error", None):
        st.error(error)

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
                try:
                    for chunk in get_ai_response(
                        user_input,
                        model_name,  # type: ignore
                        st.session_state.conversation_id,  # type: ignore,
                        temperature,
                        top_k,
                        top_p,
                        num_ctx,
                        num_predict,
                        repeat_penalty,
                        reasoning,
                    ):
                        ai_response += chunk
                        placeholder.markdown(ai_response)
                except ChatStreamError as error:
                    st.session_state.chat_error = str(error)
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()
                except PydanticValidationError as error:
                    st.session_state.chat_error = str(error.message)
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()
                except DBError as error:
                    st.session_state.chat_error = str(error.message)
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()
                except InvalidCredentials as error:
                    logger.warning(
                        f"Session expired while sending chat message: {error}"
                    )
                    redirect_to_login_after_expired_session()
                except OllamaConnectionError as error:
                    st.session_state.chat_error = str(error.message)
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()
                except ConversaionInUse as error:
                    st.session_state.chat_error = str(error.user_message)
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()
                except UnknownError as error:
                    st.session_state.chat_error = str(error.user_message)
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()
                except NetworkError as error:
                    st.session_state.chat_error = str(error.user_message)
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()
                except Exception as exception:
                    logger.exception(
                        f"Unexpected error while processing chat response - {exception}"
                    )
                    st.session_state.chat_error = (
                        "An unexpected error occurred. Please try again."
                    )
                    mark_conversation_history_stale()
                    enable_conversation()
                    st.rerun()

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": ai_response,
            }
        )
        mark_conversation_history_stale()
        enable_conversation()
        st.rerun()


if __name__ == "__main__":
    main()
