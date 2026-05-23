from datetime import UTC
from datetime import datetime as dt

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
        try:
            self.db.add(new_conversation)
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
        try:
            conversation = (
                self.db.query(Conversations)
                .where(Conversations.id == conversation_id)
                .first()
            )

            if conversation is None:
                self.db.rollback()
                raise DataBaseResourceNotFound()

            conversation.updated_at = dt.now(tz=UTC)
            self.db.add(mess)
            self.db.add(conversation)

            self.db.commit()
            logger.debug(
                f"Saved user input to DB with conversation_id = {conversation_id}"
            )
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error

    def save_bot_output(self, output: str, conversation_id: int):
        """Function saves Bot answer to user query and updates Conversation 'update_at' column in ordrer to better filter data

        Args:
            output (str): Bot answer
            conversation_id (int): ID of conversation the User and Bot participate in

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch
        """
        bot_mess = Messages(
            conversation_id=conversation_id, role="assistant", content=output
        )
        try:
            conversation = (
                self.db.query(Conversations)
                .where(Conversations.id == conversation_id)
                .first()
            )
            if conversation is None:
                raise DataBaseResourceNotFound()

            conversation.updated_at = dt.now(tz=UTC)
            self.db.add(bot_mess)
            self.db.add(conversation)

            self.db.commit()
            logger.debug(
                f"Saved LLM output to DB with conversation_id = {conversation_id}"
            )
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
        logger.debug(
            f"Returning chat messages from conversation_id = {conversation_id}"
        )
        return conversation.messages

    def user_lates_conversations_ids(self):
        """Function fetches last 10 updated user conversations

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch
            DataBaseResourceNotFound: Did not found the resource. Custom exception that FastAPI error handler will catch.

        Returns:
            _type_:list[int], Returns conversations IDs
        """
        try:
            conversations = (
                self.db.query(Conversations.id)
                .order_by(Conversations.updated_at.desc())
                .limit(10)
            ).all()  # TODO Temporary limit 10

            conversations_ids = [db_object[0] for db_object in conversations]
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error

        if not conversations_ids:
            raise DataBaseResourceNotFound()
        logger.debug("Returning user latest conversations IDs")
        return conversations_ids
