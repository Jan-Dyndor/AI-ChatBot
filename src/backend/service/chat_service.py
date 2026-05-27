from backend.chat_bot.client import ChatBotClient
from backend.database.repository import ChatRepository


class ChatService:
    def __init__(self, db: ChatRepository) -> None:
        self.db = db

    def create_user(self, email, password):
        return self.db.create_user(email, password)

    def lates_conversations_ids(self, user_id: int):
        return self.db.user_lates_conversations_ids(user_id)

    def show_chat_history(self, conversation_id, user_id):
        return self.db.chat_history(conversation_id, user_id)

    def stream_response_from_client(
        self,
        model: str,
        chat_history: list,
        user_input: str,
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
        self.db.save_user_input(user_input, conversation_id, user_id)
        print(chat_history)

        for chunk in client.stream_response(chat_history=chat_history):
            full_llm_response += chunk
            yield chunk
        self.db.save_bot_output(
            output=full_llm_response, conversation_id=conversation_id, user_id=user_id
        )

    def create_conversation(self, user_id: int) -> int:
        """Function creates new conversation on behalf od User with User ID, saves it to DB and returns conversation ID so frontend cas attach new messages to it

        Args:
            user_id (int): user ID

        Returns:
            int: Conversation ID
        """
        return self.db.create_conversation(user_id)
