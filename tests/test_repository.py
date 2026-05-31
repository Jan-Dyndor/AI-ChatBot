from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Conversations, Messages, Users
from backend.database.repository import ChatRepository
from backend.exceptions.exc import DataBaseError, DataBaseResourceNotFound, UserNotFound


#! create_conversation
def test_create_conversation_happy(session, repo_service, test_user_db):
    """Function tests create_conversation

    Args:
        session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """

    assert session.query(Conversations).first() is None
    assert session.query(Users).first() is None
    session.add(test_user_db)  # User must exist in DB
    session.commit()

    conv_id = repo_service.create_conversation(test_user_db.id)
    db_results = session.query(Conversations).first()
    assert db_results is not None
    assert conv_id == 1


def test_create_conversation_error_no_user(session, repo_service):
    """Function tests create_conversation when user with ID specified in request somehow does not exists

    Args:
        session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Conversations).first() is None
    assert session.query(Users).first() is None

    with pytest.raises(UserNotFound):
        repo_service.create_conversation(user_id=1)


def test_create_conversation_error():
    """Function tests create_conversation with DB error"""
    db_session_mock = Mock()
    db_session_mock.commit.side_effect = SQLAlchemyError()

    repo_mock = ChatRepository(db_session=db_session_mock)
    with pytest.raises(DataBaseError):
        repo_mock.create_conversation(user_id=1)

    db_session_mock.rollback.assert_called_once()


#! save_user_input
def test_save_user_input_happy(repo_service, session, test_user_db):
    """Test assumes User and Conversation exists in DB - my business logic works that way it allwasy first creates Conversation to certain User and then some operations or Messages between AI and user happen

    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None
    assert session.query(Users).first() is None

    session.add(test_user_db)  # add user to DB
    session.commit()

    conv = Conversations(user_id=test_user_db.id)
    session.add(conv)
    session.commit()

    repo_service.save_user_input(
        input="test", conversation_id=1, user_id=test_user_db.id
    )

    mess = session.query(Messages).first()
    conv_result = session.query(Conversations).first()
    user = session.query(Users).first()
    assert user.id == 1
    assert mess.conversation_id == 1
    assert mess.role == "user"
    assert mess.content == "test"
    assert session.query(Conversations).first() is not None
    assert conv_result.id == 1


def test_save_user_input_error():
    """Testing DB error.
    To invoke DB errror I do not use working DB session - I mock the session and pass it to object ChatRepository
    When Function will invoke "commit" on mocked session it will raise an error
    """
    db_session_mock = Mock()
    db_session_mock.commit.side_effect = SQLAlchemyError()

    repo_mock_session = ChatRepository(db_session=db_session_mock)

    with pytest.raises(DataBaseError):
        repo_mock_session.save_user_input(input="test", conversation_id=1, user_id=1)
    db_session_mock.rollback.assert_called_once()


def test_save_user_input_no_conversation(session, repo_service, test_user_db):
    """Test assums Conversation does not exists in DB
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    session.add(test_user_db)
    session.commit()

    with pytest.raises(DataBaseResourceNotFound):
        repo_service.save_user_input(
            input="test", conversation_id=1, user_id=test_user_db.id
        )
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None


#! save_bot_output
def test_save_bot_output_happy(session, repo_service, test_user_db):
    """Test assums Conversation exists in DB - my business logic works that way it allwasy first creates Conversation and then some operations or Messages between AI and user happen

    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None
    assert session.query(Users).first() is None
    session.add(test_user_db)
    session.commit()

    conv = Conversations(user_id=test_user_db.id)
    session.add(conv)
    session.commit()

    repo_service.save_bot_output(
        output="test", conversation_id=1, user_id=test_user_db.id
    )

    mess = session.query(Messages).first()
    conv_result = session.query(Conversations).first()
    user = session.query(Users).first()
    assert user.id == 1
    assert mess.conversation_id == 1
    assert mess.role == "assistant"
    assert mess.content == "test"
    assert session.query(Conversations).first is not None
    assert conv_result.id == 1


def test_save_bot_output_no_conversation(session, repo_service, test_user_db):
    """Test assums Conversation does not exists in DB
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    session.add(test_user_db)
    session.commit()

    with pytest.raises(DataBaseResourceNotFound):
        repo_service.save_bot_output(
            output="test", conversation_id=1, user_id=test_user_db.id
        )
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None


def test_save_bot_output_error():
    """
    Function tests saving bot output when DB errro occured
    """

    db_session_mock = Mock()
    db_session_mock.query.side_effect = SQLAlchemyError()

    repo_mock = ChatRepository(db_session=db_session_mock)

    with pytest.raises(DataBaseError):
        repo_mock.save_bot_output(output="test", conversation_id=1, user_id=1)


#! chat_history
def test_chat_history_happy_with_messages(session, repo_service, test_user_db):
    """Test fetching chat history - in conversation there are messages
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    # Test preparation
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    session.add(test_user_db)
    session.commit()
    conv_1 = Conversations(user_id=test_user_db.id)

    mess_user_1 = Messages(
        conversation_id=1, role="user", content="First user message test"
    )
    mess_bot_1 = Messages(
        conversation_id=1, role="assistant", content="AI response to first user message"
    )
    session.add_all([conv_1, mess_user_1, mess_bot_1])
    session.commit()

    # Test body
    messages = repo_service.chat_history(
        conversation_id=conv_1.id, user_id=test_user_db.id
    )
    mess_1, mess_2 = messages
    assert messages is not None
    assert mess_1.id == 1
    assert mess_1.conversation_id == 1
    assert mess_1.role == "user"
    assert mess_1.content == "First user message test"

    assert messages is not None
    assert mess_2.id == 2
    assert mess_2.conversation_id == 1
    assert mess_2.role == "assistant"
    assert mess_2.content == "AI response to first user message"


def test_chat_history_happy_no_messages(session, repo_service, test_user_db):
    """Test fetching chat history - conversation stores no messages
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    # Test preparation
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    session.add(test_user_db)
    session.commit()
    conv = Conversations(user_id=test_user_db.id)

    session.add(conv)
    session.commit()

    # Test body
    messages = repo_service.chat_history(
        conversation_id=conv.id, user_id=test_user_db.id
    )

    assert messages == []


def test_chat_history_happy_no_mess_in_conversation(session, repo_service):
    """Test fetching chat history - conversation stores no messages
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    # Test preparation
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    with pytest.raises(DataBaseResourceNotFound):
        repo_service.chat_history(conversation_id=1, user_id=1)


def test_chat_history_error():
    """
    Test fetching chat history with DB error
    """
    db_session_mock = Mock()
    db_session_mock.query.side_effect = SQLAlchemyError()

    repo_mock = ChatRepository(db_session=db_session_mock)

    with pytest.raises(DataBaseError):
        repo_mock.chat_history(conversation_id=1, user_id=1)
    db_session_mock.rollback.assert_called_once()


#! user_lates_conversations_ids


def test_user_lates_conversations_ids_happy(session, repo_service, test_user_db):
    """Test fetching user lates conversations.
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Conversations).first() is None
    assert session.query(Messages).first() is None

    session.add(test_user_db)
    session.commit()
    # Create 11 Conversation
    for _ in range(11):
        session.add(Conversations(user_id=test_user_db.id))
        session.commit()

    ids = repo_service.user_lates_conversations_ids(user_id=test_user_db.id)

    assert len(ids) == 10
    assert (
        1 not in ids
    )  # Sorting by updated_at so first conversation is the oldest one and wont be displayed


def test_user_lates_conversations_ids_no_conversations(
    session, repo_service, test_user_db
):
    """Test fetching user lates conversations. No conversations scenerio
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Conversations).first() is None
    assert session.query(Messages).first() is None
    session.add(test_user_db)
    session.commit()

    with pytest.raises(DataBaseResourceNotFound):
        repo_service.user_lates_conversations_ids(user_id=test_user_db.id)


def test_user_lates_conversations_ids_less_than_10_conversetions(
    session, repo_service, test_user_db
):
    """Test fetching user lates conversations. Less than 10 conversations
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Conversations).first() is None
    assert session.query(Messages).first() is None

    session.add(test_user_db)
    session.commit()
    for _ in range(5):
        session.add(Conversations(user_id=test_user_db.id))
        session.commit()
    ids = repo_service.user_lates_conversations_ids(user_id=test_user_db.id)
    assert ids is not None
    assert ids == [5, 4, 3, 2, 1]


def test_user_lates_conversations_ids_error():
    db_sesson_mock = Mock()
    db_sesson_mock.query.side_effect = SQLAlchemyError()

    repo_mock = ChatRepository(db_session=db_sesson_mock)

    with pytest.raises(DataBaseError):
        repo_mock.user_lates_conversations_ids(user_id=1)

    db_sesson_mock.rollback.assert_called_once()
