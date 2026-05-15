from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Messages
from backend.exceptions.exc import (
    ConversationNotFound,
    DataBaseError,
    DataBaseResourceNotFound,
)


class ChatRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_conversation(self) -> int:
        new_conversation = Conversations()
        self.db.add(new_conversation)
        try:
            self.db.commit()
            self.db.refresh(new_conversation)
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error
        return new_conversation.id

    def save_user_input(self, input: str, conversation_id: int):
        mess = Messages(conversation_id=conversation_id, role="user", content=input)
        self.db.add(mess)
        try:
            self.db.commit()
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error

    def save_bot_output(self, output: str, conversation_id: int):
        bot_mess = Messages(
            conversation_id=conversation_id, role="assistant", content=output
        )
        self.db.add(bot_mess)
        try:
            self.db.commit()
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error

    def chat_history(self, conversation_id):
        try:
            conversation = (
                self.db.query(Conversations)
                .where(Conversations.id == conversation_id)
                .first()
            )
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error

        if conversation is None:
            raise DataBaseResourceNotFound()

        if conversation.messages == []:
            raise ConversationNotFound()

        return conversation.messages
