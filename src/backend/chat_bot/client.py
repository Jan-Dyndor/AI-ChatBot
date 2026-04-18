from ollama import chat


class ChatBot:
    def __init__(
        self,
        model: str,
    ) -> None:
        self.model: str = model

    def stream_response(self, chat_history: list):
        ai_response_content: str = ""

        stream_response = chat(model=self.model, messages=chat_history, stream=True)

        for chunk in stream_response:
            content_chunk = chunk.message.content
            if content_chunk is None:
                continue
            else:
                ai_response_content += content_chunk
                yield content_chunk
