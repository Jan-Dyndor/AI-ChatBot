import pytest

from backend.database.models import Conversations, Messages
from backend.exceptions.exc import DataBaseResourceNotFound


def test_happy_create_conversation(session, repo_service):
    """Function tests create_conversation

    Args:
        session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """

    assert session.query(Conversations).first() is None
    conv_id = repo_service.create_conversation()
    db_results = session.query(Conversations).first()
    assert db_results is not None
    assert conv_id == 1


def test_save_user_input_happy(repo_service, session):
    """Test assums Conversation exists in DB - my business logic works that way it allwasy first creates Conversation and then some operations or Messages between AI and user happen

    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    conv = Conversations()
    session.add(conv)
    session.commit()

    repo_service.save_user_input(input="test", conversation_id=1)

    mess = session.query(Messages).first()
    conv_result = session.query(Conversations).first()
    assert mess.conversation_id == 1
    assert mess.role == "user"
    assert mess.content == "test"
    assert session.query(Conversations).first is not None
    assert conv_result.id == 1


def test_save_user_input_no_conversation(session, repo_service):
    """Test assums Conversation does not exists in DB
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    with pytest.raises(DataBaseResourceNotFound):
        repo_service.save_user_input(input="test", conversation_id=1)
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None


def test_save_bot_output_happy(session, repo_service):
    """Test assums Conversation exists in DB - my business logic works that way it allwasy first creates Conversation and then some operations or Messages between AI and user happen

    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    conv = Conversations()
    session.add(conv)
    session.commit()

    repo_service.save_bot_output(output="test", conversation_id=1)

    mess = session.query(Messages).first()
    conv_result = session.query(Conversations).first()
    assert mess.conversation_id == 1
    assert mess.role == "assistant"
    assert mess.content == "test"
    assert session.query(Conversations).first is not None
    assert conv_result.id == 1


def test_save_bot_output_no_conversation(session, repo_service):
    """Test assums Conversation does not exists in DB
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    with pytest.raises(DataBaseResourceNotFound):
        repo_service.save_bot_output(output="test", conversation_id=1)
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None


def test_chat_history_happy_with_messages(session, repo_service):
    """Test fetching chat history - in conversation there are messages
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    # Test preparation
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    conv_1 = Conversations()

    mess_user_1 = Messages(
        conversation_id=1, role="user", content="First user message test"
    )
    mess_bot_1 = Messages(
        conversation_id=1, role="assistant", content="AI response to first user message"
    )
    session.add_all([conv_1, mess_user_1, mess_bot_1])
    session.commit()

    # Test body
    messages = repo_service.chat_history(conversation_id=1)
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


def test_chat_history_happy_no_messages(session, repo_service):
    """Test fetching chat history - conversation stores no messages
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    # Test preparation
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    conv = Conversations()

    session.add(conv)
    session.commit()

    # Test body
    messages = repo_service.chat_history(conversation_id=1)

    assert messages == []


def test_chat_history_happy_no_conversation(session, repo_service):
    """Test fetching chat history - conversation stores no messages
    Args:
       session (_type_): db session from sessionmaker
        repo_service (_type_): ChatRepository object initialized with session
    """
    # Test preparation
    assert session.query(Messages).first() is None
    assert session.query(Conversations).first() is None

    conv = Conversations()

    session.add(conv)
    session.commit()

    # Test body
    messages = repo_service.chat_history(conversation_id=1)

    assert messages == []
