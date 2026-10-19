from datetime import UTC
from datetime import datetime as dt

from loguru import logger
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Messages, StatusMessage, Users
from backend.exceptions.exc import DataBaseError, DataBaseResourceNotFound, UserNotFound


class ChatRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def create_conversation(self, user_id: int) -> int:
        """Function creates new conversation and saves it into DB

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch

        Returns:
            int: conversation ID to frontend

        """
        try:
            user = self.db.query(Users).where(Users.id == user_id).first()
        except SQLAlchemyError as ex:
            raise DataBaseError() from ex

        if not user:
            logger.warning(f"user with ID {user_id} not found")
            raise UserNotFound(user_id=user_id)

        new_conversation = Conversations(user_id=user_id)
        try:
            self.db.add(new_conversation)
            self.db.commit()
            self.db.refresh(new_conversation)
        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error
        logger.debug(
            f"Created conversation with ID {new_conversation.id} attached to user {user.id}"
        )
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

        mess = Messages(
            conversation_id=conversation_id,
            role="user",
            content=input,
            status=StatusMessage.PENDING,
        )

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
                logger.warning(
                    f"Conversation not found or not owned by user. user_id={user_id}, conversation_id={conversation_id}"
                )
                raise DataBaseResourceNotFound()

            conversation.updated_at = dt.now(tz=UTC)
            self.db.add(mess)
            self.db.add(conversation)

            self.db.commit()
            logger.debug(
                f"Saved user {user_id} input  to conversation {conversation_id}"
            )
            return mess.id
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
            conversation_id=conversation_id,
            role="assistant",
            content=output,
            status=StatusMessage.PENDING,
        )

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
                logger.warning(
                    f"Conversation not found or not owned by user. user_id={user_id}, conversation_id={conversation_id}"
                )
                raise DataBaseResourceNotFound()

            conversation.updated_at = dt.now(tz=UTC)
            self.db.add(bot_mess)
            self.db.add(conversation)

            self.db.commit()
            logger.debug(
                f"Saved LLM output with to conversation {conversation_id} connected to user {user_id}"
            )
            return bot_mess.id
        except SQLAlchemyError as error:
            logger.exception(
                f"Can not save LLM output. Failed to save bot output after streaming response Conversation_ID: {conversation_id} User_ID: {user_id}"
            )
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
            # 1. Check if conversation exists and belongs to user
            conversation = (
                self.db.query(Conversations)
                .where(
                    Conversations.id == conversation_id,
                    Conversations.user_id == user_id,
                )
                .first()
            )

            if conversation is None:
                logger.warning(
                    f"User {user_id} does not own conversation {conversation_id}"
                )
                raise DataBaseResourceNotFound()

            # 2. Fetch only COMPLETED messages
            messages = (
                self.db.query(Messages)
                .where(
                    Messages.conversation_id == conversation_id,
                    Messages.status == StatusMessage.COMPLETED,
                )
                .order_by(Messages.created_at.asc(), Messages.id.asc())
                .all()
            )
            if not messages:
                logger.info(
                    f"No completed messages found in conversation {conversation_id}"
                )

            logger.debug(
                f"Returning chat messages from conversation {conversation_id} attached to user {user_id}"
            )
            return messages

        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception(
                f"Exception occured during fetching chat history from conversation{conversation_id} User_ID: {user_id}"
            )
            raise DataBaseError() from error

    def user_lates_conversations_ids(self, user_id: int) -> list[tuple]:
        """Function fetches last 10 updated user conversations.
        If conversation has not yet title (summary filed in table is NULL) it uses a placeholder to populate that value for better user experience

        Raises:
            DataBaseError: Custom exception that FastAPI error handler will catch
            DataBaseResourceNotFound: Did not found the resource. Custom exception that FastAPI error handler will catch.

        Returns:
            list[int]: list of latest 10 users conversations
        """
        try:
            conversation_id_sumamry: list[tuple] = (
                self.db.query(Conversations.id, Conversations.summary)
                .where(Conversations.user_id == user_id)
                .order_by(Conversations.updated_at.desc())
                .limit(10)
            ).all()  #  Temporary limit 10

        except SQLAlchemyError as error:
            self.db.rollback()
            raise DataBaseError() from error
        if not conversation_id_sumamry:
            logger.warning(f"User {user_id} does not stores any conversations")
            raise DataBaseResourceNotFound()
        if len(conversation_id_sumamry) == 1:
            logger.debug(f"User {user_id} does not possess previous conversations")
            return []

        id_summary: list[tuple] = []
        for id, summary in conversation_id_sumamry:
            if summary is None:
                summary = "New Conversation"
            id_summary.append((id, summary))

        logger.debug(f"Returning user {user_id} latest conversations IDs")
        return id_summary

    def conversation_summary_presence(self, conversation_id: int, user_id: int) -> bool:
        """Function checks user conversation if it already has SUMMARY field populated in DB

        Args:
            conversation_id (int):
            user_id (int):

        Raises:
            DataBaseResourceNotFound: Did not found the resource. Custom exception that FastAPI error handler will catch.

        Returns:
            bool: True if summary is present , False if not
        """
        try:
            conversation: tuple | None = (
                self.db.query(Conversations.summary)
                .where(
                    Conversations.user_id == user_id,
                    Conversations.id == conversation_id,
                )
                .first()
            )
        except SQLAlchemyError as error:
            raise DataBaseError() from error

        if not conversation:
            logger.warning(
                f"User {user_id} does not possess conversation {conversation_id}"
            )
            raise DataBaseResourceNotFound()

        if conversation[0] is None:
            logger.debug(
                f"User {user_id} conversation {conversation_id} does not have summary"
            )
            return False
        else:
            logger.debug(
                f"User {user_id} conversation {conversation_id} already have summary"
            )
            return True

    def save_conversation_summary(
        self, conversation_id: int, user_id: int, generated_summary: str
    ) -> None:
        """Function saves AI generated conversation summary
        Args:
            conversation_id (int):
            user_id (int):
            generated_summary (str):
        """
        try:
            summary_db = (
                update(Conversations)
                .where(
                    Conversations.id == conversation_id,
                    Conversations.user_id == user_id,
                )
                .values(summary=generated_summary)
            )

            self.db.execute(summary_db)
            self.db.commit()
            logger.debug(
                f"Saving user {user_id} summary to conversation {conversation_id}"
            )
        except SQLAlchemyError as error:
            raise DataBaseError() from error

    def validate_conversation_access(self, conversation_id: int, user_id: int):
        """Validate that a conversation exists and belongs to the given user.

        Args:
            conversation_id (int): ID of the conversation being accessed.
            user_id (int): ID of the user requesting access.

        Raises:
            DataBaseError: Raised when the database query fails.
            DataBaseResourceNotFound: Raised when the conversation does not exist
                or does not belong to the given user.
        """

        try:
            conversation = (
                self.db.query(Conversations.id)
                .where(
                    Conversations.id == conversation_id,
                    Conversations.user_id == user_id,
                )
                .first()
            )
        except SQLAlchemyError as error:
            logger.exception(
                f"Can not save LLM output. Failed to save bot output after streaming response Conversation_ID: {conversation_id} User_ID: {user_id}"
            )
            raise DataBaseError() from error

        if conversation is None:
            raise DataBaseResourceNotFound()

    def update_bot_message(
        self,
        conversation_id: int,
        user_id: int,
        llm_output: str,
        message_id: int,
        update_status: StatusMessage,
    ):

        try:
            bot_mess = self.db.query(Messages).where(Messages.id == message_id).first()

            if bot_mess is None:
                logger.warning(
                    f"Conversation not found or not owned by user. user_id={user_id}, conversation_id={conversation_id}"
                )
                raise DataBaseResourceNotFound()

            bot_mess.content = llm_output
            bot_mess.status = update_status
            self.db.commit()

        except SQLAlchemyError as error:
            logger.exception(
                f"Can not save LLM output. Failed to save bot output after streaming response Conversation_ID: {conversation_id} User_ID: {user_id}"
            )
            self.db.rollback()
            raise DataBaseError() from error

    def update_user_message(
        self,
        conversation_id: int,
        user_id: int,
        message_id: int,
        update_status: StatusMessage,
    ):

        try:
            user_mess = self.db.query(Messages).where(Messages.id == message_id).first()

            if user_mess is None:
                logger.warning(
                    f"Conversation not found or not owned by user. user_id={user_id}, conversation_id={conversation_id}"
                )
                raise DataBaseResourceNotFound()

            user_mess.status = update_status
            self.db.commit()

        except SQLAlchemyError as error:
            logger.exception(
                f"Can not update User query. Failed to update user query after streaming response Conversation_ID: {conversation_id} User_ID: {user_id}"
            )
            self.db.rollback()
            raise DataBaseError() from error
