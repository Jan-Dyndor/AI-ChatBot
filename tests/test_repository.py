from unittest.mock import MagicMock, Mock

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
