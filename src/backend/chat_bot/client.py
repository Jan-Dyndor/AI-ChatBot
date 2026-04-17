from ollama import chat


class ChatBot:
    def __init__(
        self,
        model: str,
    ) -> None:
        self.model: str = model
        self.history: list = (
            []
        )  # For now histry is saved in object itself. Statefull architecture, later we will move into Stateless

    def stream_response(self, user_input: str):
        message = {
            "role": "user",
            "content": user_input,
        }
        self.history.append(message)
        ai_response_content: str = ""

        stream_response = chat(model=self.model, messages=self.history, stream=True)

        for chunk in stream_response:
            content_chunk = chunk.message.content
            if content_chunk is None:
                continue
            else:
                ai_response_content += content_chunk
                yield content_chunk

        ai_message: dict = {"role": "assistant", "content": ai_response_content}

        self.history.append(ai_message)


ai_bot = ChatBot(
    "llama3:8b"
)  # This will eb changed later on Statless architecture - one object constais all history
