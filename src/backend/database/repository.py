from src.backend.database.models import Conversations, Messages


class ChatRepository:
    def __init__(self, db_session) -> None:
        self.db = db_session

    def save_user_input(self, input):
        # example_con = Conversations(
        #     id=1
        # )  # TODO temporaty id =1 , figure out latrer how to switch between conversetions so now i do not create another object
        example_mess = Messages(conversation_id=1, role="user", content=input)
        # self.db.add(example_con)
        self.db.add(example_mess)
        self.db.commit()

    def save_bot_output(self, output):
        bot_mess = Messages(conversation_id=1, role="assistant", content=output)
        self.db.add(bot_mess)
        self.db.commit()

    def chat_history(self):
        conversation = self.db.query(Conversations).where(Conversations.id == 1).first()
        # print("conversation:", conversation)
        # print("type:", type(conversation))

        # if conversation is None:
        #     print("No conversation found")
        #     return []
        # role = ""
        # print("messages:", conversation.messages)
        # for mess in conversation.messages:
        #     role += " " + mess.role
        # print("messages type:", type(conversation.messages))
        # return role
        return conversation.messages
