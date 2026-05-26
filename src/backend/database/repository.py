from datetime import UTC
from datetime import datetime as dt

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Messages, Users
from backend.exceptions.exc import (
    DataBaseError,
    DataBaseResourceNotFound,
)


class ChatRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_user(self, email, password) -> str:
        """Function will create user

        Args:
            email (str)
            password (str): password_hash

        Returns:
            str: User email
        """
        user = Users(email=email, password_hash=password)
        self.db.add(user)
        self.db.commit()
        return user.email

    def create_conversation(self, user_id: int) -> int:
        """Function creates new conversation and saves it into DB

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch

        Returns:
            int: conversation ID to frontend

        """
        # TODO crete conversation only oif USER with this ID exists! check other functions

        user = self.db.query(Users).where(Users.id == user_id).first()
        if not user:
            raise DataBaseResourceNotFound()  # TODO Here differen error type liek User not found

        new_conversation = Conversations(user_id=user_id)
        try:
            self.db.add(new_conversation)
            self.db.commit()
            self.db.refresh(new_conversation)
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error
        return new_conversation.id

    def save_user_input(self, input: str, conversation_id: int, user_id: int):
        """Function creates Message object, adds user input to it and attach this Message to User Conversation

        Args:
            input (str): User message
            conversation_id (int): ID of conversation
            user_id (int): User ID

        Raises:
            DataBaseResourceNotFound: Custom exception that FastAPI error handler will catch. Occures when query result is None
            DataBaseError: Genral SQLAlchemy error
        """
        mess = Messages(conversation_id=conversation_id, role="user", content=input)
        try:
            conversation = (
                self.db.query(Conversations)
                .where(
                    Conversations.id == conversation_id,
                    Conversations.user_id == user_id,
                )
                .first()
            )

            if conversation is None:
                self.db.rollback()
                raise DataBaseResourceNotFound()  # TODO later check if its needed to add different error now

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

    def save_bot_output(self, output: str, conversation_id: int, user_id: int):
        """Function creates Message object, adds LLm output to it and attach this Message to User Conversation

        Args:
            output (str): LLM message
            conversation_id (int): ID of conversation
            user_id (int): User ID

        Raises:
            DataBaseResourceNotFound: Custom exception that FastAPI error handler will catch. Occures when query result is None
            DataBaseError: Genral SQLAlchemy error
        """
        bot_mess = Messages(
            conversation_id=conversation_id, role="assistant", content=output
        )
        try:
            conversation = (
                self.db.query(Conversations)
                .where(
                    Conversations.id == conversation_id,
                    Conversations.user_id == user_id,
                )
                .first()  # TODO this can be done simpler with SQLAlchemy relations. Check that later on
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

    def chat_history(self, conversation_id: int, user_id: int) -> list[Messages]:
        """Function returns chat history between User and Bot

        Args:
            conversation_id (int): ID of conversation
            user_id (int): User ID

        Raises:
            DataBaseResourceNotFound: Custom exception that FastAPI error handler will catch. Occures when query result is None
            DataBaseError: Genral SQLAlchemy error

        Returns:
            list[Messages]: list of SQLAlchemy DB models. Later converted by Pydantic
        """
        try:
            conversation = (
                self.db.query(Conversations)
                .where(
                    Conversations.id == conversation_id,
                    Conversations.user_id
                    == user_id,  # TODO this can be done simpler with SQLAlchemy relations. Check that later on
                )
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

    def user_lates_conversations_ids(self, user_id: int) -> list[int]:
        """Function fetches last 10 updated user conversations

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch
            DataBaseResourceNotFound: Did not found the resource. Custom exception that FastAPI error handler will catch.

        Returns:
            list[int]: list of latest 10 users conversations
        """
        try:
            conversations = (
                self.db.query(Conversations.id)
                .where(Conversations.user_id == user_id)
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
