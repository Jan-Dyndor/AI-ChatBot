import ollama
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langsmith import traceable

from backend.configuration.logging_config import logger
from backend.exceptions.exc import (
    OllamaConnectionError,
    OllamaEmbeddingModelError,
    OllamaError,
    OllamaModelError,
)


class ChatBotClient:
    """Stateless class to communicate with Ollama"""

    @traceable(name="create_conversation_title")
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

            Create a short conversation title for the following USER MESSAGE: {user_input}. Return only the title."
            """

        try:
            llm = ChatOllama(
                model=model, num_predict=20, temperature=0, reasoning=False
            )
            prompt = PromptTemplate.from_template(system_prompt)

            chain = prompt | llm
            response = chain.invoke({"user_input": user_input})
            return str(response.content).strip()

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

    def get_llm(
        self,
        model,
        temperature: float,
        top_k,
        top_p,
        num_ctx,
        num_predict,
        repeat_penalty,
        is_thinking,
    ) -> BaseChatModel:
        """Create and configure an Ollama chat model.

        Args:
            model (str): Name of the Ollama model to use.
            temperature (float): Controls the randomness of generated responses.
            top_k (int): Limits token selection to the top K candidates.
            top_p (float): Sets the cumulative probability threshold for token sampling.
            num_ctx (int): Maximum context window size in tokens.
            num_predict (int): Maximum number of tokens to generate.
            repeat_penalty (float): Penalty applied to repeated tokens.
            is_thinking (bool): Enables or disables reasoning mode for supported models.

        Returns:
            BaseChatModel: Configured Ollama chat model instance.
        """

        return ChatOllama(
            model=model,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            num_ctx=num_ctx,
            num_predict=num_predict,
            repeat_penalty=repeat_penalty,
            reasoning=is_thinking,
        )
