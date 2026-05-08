from backend.chat_bot.client import ChatBotClient
from src.backend.database.repository import ChatRepository


class ChatService:
    def __init__(self, db: ChatRepository) -> None:
        self.db = db

    def stream_response_from_client(self, model: str, chat_history: list):
        """Function creates ChatBotClient object with choosen model, and stream responses from LLM

        Args:
            model (str): LLM model name
            chat_history (list): user chat history

        Returns:
            _type_: yields chunks of LLM responses
        """

        client = ChatBotClient(model)
        self.db.save_chat()
        return client.stream_response(chat_history=chat_history)
