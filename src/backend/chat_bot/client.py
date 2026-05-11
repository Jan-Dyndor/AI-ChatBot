import httpx
import ollama
from ollama import chat

from backend.configuration.logging_config import logger


class ChatBotClient:
    def __init__(
        self,
        model: str,
    ) -> None:
        self.model: str = model

    def stream_response(self, chat_history: list):
        """Function streams responses from LLM using Ollama

        Args:
            chat_history (list): chat history, list of dics

        Yields:
            _type_: strigns (LLM responses / ERROR messages)
        """

        try:
            stream_response = chat(model=self.model, messages=chat_history, stream=True)

            for chunk in stream_response:
                content_chunk = chunk.message.content
                if content_chunk is None:
                    continue
                else:
                    yield content_chunk
        except httpx.ConnectError as error:
            logger.exception(error)
            yield "\n\n\n\n\n[ERROR] Ollama is not available. Check if its running on your system"
            return
        except ollama.ResponseError as error:
            if error.status_code == 404:
                logger.exception(error)
                yield f"\n\n\n\n\n[ERROR] Ollama error: {error.status_code}. Ollama model might not exists or its not downloaded"
                return
            else:
                logger.exception(error)
                yield f"\n\n\n\n\n[ERROR] Ollama error: {error.status_code}."
                return
        except httpx.RemoteProtocolError as error:
            yield "\n\n\n\n\n [ERROR] Ollama stopped responding and is unavailable. Check if its running on your system"
            logger.exception(error)
            return
