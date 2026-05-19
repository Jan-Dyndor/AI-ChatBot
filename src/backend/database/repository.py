from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Messages
from backend.exceptions.exc import (
    DataBaseError,
    DataBaseResourceNotFound,
)


class ChatRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_conversation(self) -> int:
        """Function creates new conversation and saves it into DB

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch

        Returns:
            int: conversation ID to frontend
        """
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
        """Function saves user query to ChatBot

        Args:
            input (str): user query
            conversation_id (int): ID of conversation the User and Bot participate in

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch
        """
        mess = Messages(conversation_id=conversation_id, role="user", content=input)
        self.db.add(mess)
        try:
            self.db.commit()
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error

    def save_bot_output(self, output: str, conversation_id: int):
        """Function saves Bot answer to user query

        Args:
            output (str): Bot answer
            conversation_id (int): ID of conversation the User and Bot participate in

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch
        """
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
        """Function returns chat history between User and Bot

        Args:
            conversation_id (int): ID of conversation the User and Bot participate in

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch
            DataBaseResourceNotFound: Did not found the resource. Custom exception that FastAPI error handler will catch.

        Returns:
            _type_: _description_
        """
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
            logger.info(
                f"Conversation with ID {conversation_id} does not yet stores data"
            )

        return conversation.messages

    def user_lates_conversations_ids(self):
        try:
            conversations = (
                self.db.query(Conversations.id)
                .order_by(Conversations.updated_at.desc())
                .offset(1)
                .limit(10)
            ).all()  # TODO Temporary limit 10, later add not to include the first one since it may be the current conversation

            conversations_ids = [db_object[0] for db_object in conversations]
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error

        if not conversations_ids:
            raise DataBaseResourceNotFound()
        return conversations_ids
