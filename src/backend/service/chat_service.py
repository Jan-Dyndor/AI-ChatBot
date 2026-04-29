from backend.chat_bot.client import ChatBotClient


class ChatService:
    def stream_response_from_client(self, model: str, chat_history: list):

        client = ChatBotClient(model)
        return client.stream_response(chat_history=chat_history)
