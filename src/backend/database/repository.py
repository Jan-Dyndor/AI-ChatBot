from src.backend.database.models import Messages, Conversations


class ChatRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def save_chat(self):
        example_con = Conversations()
        example_mess = Messages(conversation_id=1, role="user", content="TEST")
        self.db.add(example_con)
        self.db.add(example_mess)
        self.db.commit()
