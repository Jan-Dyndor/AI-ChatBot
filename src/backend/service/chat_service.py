from loguru import logger

from backend.chat_bot.client import ChatBotClient
from backend.database.chat_repository import ChatRepository
from backend.exceptions.exc import DataBaseError, DataBaseResourceNotFound


class ChatService:
    def __init__(self, db: ChatRepository) -> None:
        self.db = db

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
        client = ChatBotClient(model)

        conversation_summary = self.db.conversation_summary_presence(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation_summary:
            generated_summary = client.create_conversation_title(user_input=user_input)
            self.db.save_conversation_summary(
                conversation_id=conversation_id,
                user_id=user_id,
                generated_summary=generated_summary,
            )

    def save_bot_output(self, output, conversation_id, user_id):
        return self.db.save_bot_output(output, conversation_id, user_id)

    def stream_response_from_client(
        self,
        model: str,
        chat_history: list,
        conversation_id: int,
        user_id: int,
    ):
        """Function creates ChatBotClient object with choosen model, and stream responses from LLM using yield. It also creates full model response to save it in DB.

        Args:
            model (str): AI model name
            chat_history (list): list of previous conversations
            user_input (str): user current message
            conversation_id (int): ID of conversation
            user_id (int): ID of User

        Yields:
            str: LLM yields chunks of response
        """
        full_llm_response: str = ""
        client = ChatBotClient(model)

        for chunk in client.stream_response(chat_history=chat_history):
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

    def create_conversation(self, user_id: int) -> int:
        """Function creates new conversation on behalf od User with User ID, saves it to DB and returns conversation ID so frontend can attach new messages to it

        Args:
            user_id (int): user ID

        Returns:
            int: Conversation ID
        """
        return self.db.create_conversation(user_id)
