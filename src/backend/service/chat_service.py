from threading import Lock

from loguru import logger

from backend.api.schemas.pydantic_schemas import Message
from backend.chat_bot.client import ChatBotClient
from backend.database.chat_repository import ChatRepository
from backend.database.models import Messages
from backend.exceptions.exc import DataBaseError, DataBaseResourceNotFound


class ChatService:
    def __init__(self, db: ChatRepository, chat_bot_client: ChatBotClient) -> None:
        self.db = db
        self.chat_bot_client = chat_bot_client

    def lates_conversations_ids(self, user_id: int):
        return self.db.user_lates_conversations_ids(user_id)

    def show_chat_history(self, conversation_id, user_id):
        return self.db.chat_history(conversation_id, user_id)

    def save_user_input(self, user_input, conversation_id, user_id):
        return self.db.save_user_input(
            input=user_input, conversation_id=conversation_id, user_id=user_id
        )

    def conversation_summary(
        self, user_input: str, conversation_id: int, user_id: int, model: str
    ):
        """Function is responsible for conversation summary logic.
        If summary not present - creates it.

        Args:
            user_input (str):
            conversation_id (int):
            user_id (int):
            model (str):
        """

        conversation_summary = self.db.conversation_summary_presence(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation_summary:
            generated_summary = self.chat_bot_client.create_conversation_title(
                user_input=user_input, model=model
            )
            self.db.save_conversation_summary(
                conversation_id=conversation_id,
                user_id=user_id,
                generated_summary=generated_summary,
            )

    def save_bot_output(self, output, conversation_id, user_id):
        return self.db.save_bot_output(output, conversation_id, user_id)

    def thread_save_streaming_response(
        self,
        lock_object: Lock,
        model: str,
        conversation_id: int,
        user_id: int,
        temperature: float,
        top_k: int,
        top_p: float,
        num_ctx: int,
        num_predict: int,
        repeat_penalty: float,
        is_thinking: bool,
        chat_history: list[dict],
    ):
        """Stream the LLM response while holding the conversation lock.

        This wrapper delegates response generation to
        `stream_response_from_client` and yields each generated chunk.

        The provided lock must already be acquired before this generator starts.
        It remains active for the entire streaming lifecycle and is released in
        the `finally` block when the stream finishes, raises an exception, or is
        closed. This prevents another request from modifying the same conversation
        while the current assistant response is still being generated.

        Keep the conversation locked for the entire streaming lifecycle.

        FastAPI returns a StreamingResponse before the response generator finishes
        its work. Therefore, releasing the lock directly in the endpoint would unlock
        the conversation while the LLM is still generating and streaming its response.

        This wrapper yields all chunks produced by `stream_response_from_client` and
        releases the lock in the `finally` block. This guarantees that the lock is
        released when streaming finishes, fails with an exception, or is closed.

        The lock must be acquired before it is passed to this function. This function
        does not acquire the lock; it only guarantees its release.


        """
        try:
            for chunk in self.stream_response_from_client(
                model,
                conversation_id,
                user_id,
                temperature,
                top_k,
                top_p,
                num_ctx,
                num_predict,
                repeat_penalty,
                is_thinking,
                chat_history,
            ):
                yield chunk

        finally:
            #! realase LOCK after streaming
            lock_object.release()

    def stream_response_from_client(
        self,
        model: str,
        conversation_id: int,
        user_id: int,
        temperature: float,
        top_k: int,
        top_p: float,
        num_ctx: int,
        num_predict: int,
        repeat_penalty: float,
        is_thinking: bool,
        chat_history: list[dict],
    ):
        """Function creates ChatBotClient object with choosen model, and parameters, stream responses from LLM using yield. It also creates full model response to save it in DB.

        Args:
            model (str): AI model name
            conversation_id (int): ID of conversation
            user_id (int): ID of User
            temperature (float):
            top_k (int):
            top_p (float):
            num_ctx (int):
            num_predict (int):
            repeat_penalty (float):

        Yields:
            str: LLM yields chunks of response
        """

        full_llm_response: str = ""
        for chunk in self.chat_bot_client.stream_response(
            model=model,
            chat_history=chat_history,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            num_ctx=num_ctx,
            num_predict=num_predict,
            repeat_penalty=repeat_penalty,
            is_thinking=is_thinking,
        ):
            full_llm_response += chunk
            yield chunk
        #! Save bot output - I can not raise errors and let them go to FastAPI exception handler, since StreamingResponse already started and I can not change HTTP status code. Otherwise I Will get errors like below:
        # raise RuntimeError("Caught handled exception, but response already started.")
        try:
            self.db.save_bot_output(
                output=full_llm_response,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        except DataBaseResourceNotFound:
            logger.exception(
                f"Can not save LLM output. Conversation disappeared or access invalid after streaming Conversation_ID: {conversation_id} User_ID: {user_id}"
            )
        except DataBaseError:
            logger.exception(
                f"Can not save LLM output. Failed to save bot output after streaming response Conversation_ID: {conversation_id} User_ID: {user_id}"
            )

    def fetch_chat_history(self, conversation_id: int, user_id: int) -> list[dict]:
        """Fucntion fetches messages beetween user and LLM from DB

        Args:
            conversation_id (int):
            user_id (int):

        Returns:
            list[dict]: User - Bot messages
        """

        chat_history_sql: list[Messages] = self.db.chat_history(
            conversation_id=conversation_id, user_id=user_id
        )

        chat_history = []
        for message in chat_history_sql:
            chat_history.append(Message.model_validate(message).model_dump())

        return chat_history

    def create_conversation(self, user_id: int) -> int:
        """Function creates new conversation on behalf od User with User ID, saves it to DB and returns conversation ID so frontend can attach new messages to it

        Args:
            user_id (int): user ID

        Returns:
            int: Conversation ID
        """
        return self.db.create_conversation(user_id)

    def show_avaliable_models(
        self,
    ):
        return self.chat_bot_client.show_avaliable_models()
