from backend.database.models import Conversations, Messages
from backend.exceptions.exc import ConversationNotFound


class ChatRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_conversation(self) -> int:
        new_conversation = Conversations()
        self.db.add(new_conversation)
        self.db.commit()
        return new_conversation.id

    def save_user_input(self, input: str, conversation_id: int):
        mess = Messages(conversation_id=conversation_id, role="user", content=input)
        self.db.add(mess)
        self.db.commit()

    def save_bot_output(self, output: str, conversation_id: int):
        bot_mess = Messages(
            conversation_id=conversation_id, role="assistant", content=output
        )
        self.db.add(bot_mess)
        self.db.commit()

    def chat_history(self, conversation_id):
        conversation = (
            self.db.query(Conversations)
            .where(Conversations.id == conversation_id)
            .first()
        )
        if conversation.messages == []:
            raise ConversationNotFound()
        return conversation.messages
