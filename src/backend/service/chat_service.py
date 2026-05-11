from backend.chat_bot.client import ChatBotClient
from src.backend.database.repository import ChatRepository


class ChatService:
    def __init__(self, db: ChatRepository) -> None:
        self.db = db

    def show_chat_history(self):
        # TODO narize zakladam conversation_id = 1
        # Potem dodaj oblusge bledow
        return self.db.chat_history()

    def stream_response_from_client(
        self, model: str, chat_history: list, user_input: str
    ):
        """Function creates ChatBotClient object with choosen model, and stream responses from LLM using yield. It also creates full model response to save it in DB.

        Args:
            model (str): LLM model name
            chat_history (list): user chat history

        Returns:
            _type_: yields chunks of LLM responses
        """
        full_llm_response: str = ""
        client = ChatBotClient(model)
        self.db.save_user_input(user_input)

        for chunk in client.stream_response(chat_history=chat_history):
            full_llm_response += chunk
            yield chunk
        self.db.save_bot_output(output=full_llm_response)
