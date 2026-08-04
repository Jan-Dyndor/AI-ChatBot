import httpx
import ollama
from ollama import chat, generate

from backend.configuration.logging_config import logger
from backend.exceptions.exc import (
    OllamaConnectionError,
    OllamaEmbeddingModelError,
    OllamaError,
    OllamaModelError,
)


class ChatBotClient:
    """Stateless class to communicate with Ollama"""

    def stream_response(
        self,
        model,
        chat_history: list,
        temperature,
        top_k,
        top_p,
        num_ctx,
        num_predict,
        repeat_penalty,
        is_thinking,
    ):
        """Function streams responses from LLM using Ollama

        Args:
            chat_history (list): chat history, list of dics

        Yields:
            _type_: strigns (LLM responses / ERROR messages)
        """

        try:
            stream_response = chat(
                model=model,
                messages=chat_history,
                stream=True,
                think=is_thinking,
                options={
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                    "num_ctx": num_ctx,
                    "num_predict": num_predict,
                    "repeat_penalty": repeat_penalty,
                },
            )

            for chunk in stream_response:
                content_chunk = chunk.message.content
                if content_chunk is None:
                    continue
                else:
                    yield content_chunk
        # Unforunatelly this is StreamingResponse = generator. Before it starts sending data FastAPI already sends response as 200
        # It does not make sens to raise exception there so only info to frontend will be this yeld messages
        except httpx.ConnectError:
            logger.exception("Ollama in unavaliable")
            yield "\n\n\n\n\n[ERROR] Ollama is not available. Check if its running on your system"
            return
        except ollama.ResponseError as error:
            if error.status_code == 404:
                logger.exception(
                    f"Ollama error: {error.status_code}. Ollama model might not exists or its not downloaded"
                )
                yield "\n\n\n\n\n[ERROR] Ollama error. Ollama model might not exists or its not downloaded"
                return
            elif error.status_code == 400:
                logger.exception(f"Ollama error: {error.status_code}. Error - {error}")
                yield "\n\n\n\n\n[ERROR] Ollama error. Keep in mind that embedding models can not generate responses and some models do not support THINKING"
                return
            else:
                logger.exception(f"Ollama error {error.status_code}")
                yield f"\n\n\n\n\n[ERROR] Ollama error: {error.status_code}."
                return
        except httpx.RemoteProtocolError:
            logger.exception(
                "Ollama stopped responding and is unavailable. Check if its running on your system"
            )
            yield "\n\n\n\n\n [ERROR] Ollama stopped responding and is unavailable. Check if its running on your system"
            return

    def create_conversation_title(self, user_input: str, model: str) -> str:
        """Function generated conversation summary based on user prompt

        Args:
            user_input (str): user prompt to AI

        Returns:
            str: conversation title
        """
        system_prompt = """
            You generate short conversation titles for a conversational AI app.

            Based only on the user's first message, create a concise title for the conversation.

            Rules:
            - Return only the title.
            - Use the same language as the user's message.
            - Maximum 6 words.
            - Prefer 2 to 4 words.
            - Do not use quotation marks.
            - Do not add a period.
            - Do not answer the user's message.
            - If the message is only a greeting, small talk, thanks, or too vague to identify a topic, return a casual conversation title.
            - Do not return "New Conversation"; that value is reserved for the app UI placeholder before a title is generated.

            Examples:
            User: "How do I set up a debugger in FastAPI?"
            Title: "FastAPI Debugging"

            User: "Can you explain JWT authentication?"
            Title: "JWT Authentication"

            User: "I have a problem with a 422 error in requests"
            Title: "API 422 Error"

            User: "Hi"
            Title: "Casual Conversation"

            User: "How should I structure my FastAPI project?"
            Title: "FastAPI Project Structure"

            User: "Why is my database query returning None?"
            Title: "Database Query Issue"

            User: "Explain the difference between REST and GraphQL"
            Title: "REST vs GraphQL"
            """

        try:
            response = generate(
                model=model,
                prompt=f"Create a short conversation title for the following USER MESSAGE: {user_input}. Return only the title.",
                system=system_prompt,
                stream=False,
                think=False,
                options={"temperature": 0, "num_predict": 15},
            )
            return response["response"].strip()

        except ConnectionError as error:
            raise OllamaConnectionError() from error

        except ollama.ResponseError as error:
            if error.status_code == 404:
                raise OllamaModelError() from error
            elif error.status_code == 400:
                raise OllamaEmbeddingModelError() from error
            else:
                raise OllamaError()

    def show_avaliable_models(self):
        """Function returns list of avaliable models via Ollama"""
        try:
            model_list = ollama.list()
            logger.debug("Returning avaliable AI models")
            return model_list
        except ConnectionError as error:
            raise OllamaConnectionError from error
        except ollama.ResponseError as error:
            raise OllamaError() from error
