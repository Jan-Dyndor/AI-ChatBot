import httpx
import ollama
from ollama import chat

from backend.configuration.logging_config import logger
from backend.exceptions.exc import (
    OllamaConnectionError,
    OllamaConnectionStoppedError,
    OllamaError,
    OllamaModelError,
)


class ChatBotClient:
    def __init__(
        self,
        model: str,
    ) -> None:
        self.model: str = model

    def stream_response(self, chat_history: list):
        """Function streams responses form LLM using Ollama

        Args:
            chat_history (list): chat history, list of dics

        Raises:
            OllamaConnectionError: Cound not connect to Ollama
            OllamaModelError: Wrong model name or model not downloaded
            OllamaError: Ollama client faced some errors
            OllamaConnectionStoppedError: Ollama client was working, connection was secured but somehow it stopped working

        Yields:
            _type_: strigns (LLM responses / ERROR messages)
        """

        ai_response_content: str = ""

        try:
            stream_response = chat(model=self.model, messages=chat_history, stream=True)

            for chunk in stream_response:
                content_chunk = chunk.message.content
                if content_chunk is None:
                    continue
                else:
                    ai_response_content += content_chunk
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
