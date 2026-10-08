from threading import Lock

import httpx
import ollama
from langchain_classic.chains import (
    create_history_aware_retriever,
    create_retrieval_chain,
)
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langsmith import traceable
from loguru import logger

from backend.api.schemas.pydantic_schemas import Message
from backend.chat_bot.client import ChatBotClient
from backend.database.chat_repository import ChatRepository
from backend.database.models import Messages
from backend.exceptions.exc import DataBaseError, DataBaseResourceNotFound
from RAG.file_vector_repository import FileVectorStorage


class ChatService:
    def __init__(
        self,
        db: ChatRepository,
        chat_bot_client: ChatBotClient,
        file_vector_storage: FileVectorStorage,
    ) -> None:
        self.db = db
        self.chat_bot_client = chat_bot_client
        self.vector_storage = file_vector_storage

    def lates_conversations_ids(self, user_id: int):
        return self.db.user_lates_conversations_ids(user_id)

    def show_chat_history(self, conversation_id, user_id):
        return self.db.chat_history(conversation_id, user_id)

    def save_user_input(self, user_input, conversation_id, user_id):
        return self.db.save_user_input(
            input=user_input, conversation_id=conversation_id, user_id=user_id
        )

    def conversation_summary(
        self, user_input: str, conversation_id: int, user_id: int, model: str
    ):
        """Function is responsible for conversation summary logic.
        If summary not present - creates it.

        Args:
            user_input (str):
            conversation_id (int):
            user_id (int):
            model (str):
        """

        conversation_summary = self.db.conversation_summary_presence(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation_summary:
            generated_summary = self.chat_bot_client.create_conversation_title(
                user_input=user_input, model=model
            )
            self.db.save_conversation_summary(
                conversation_id=conversation_id,
                user_id=user_id,
                generated_summary=generated_summary,
            )

    def save_bot_output(self, output, conversation_id, user_id):
        return self.db.save_bot_output(output, conversation_id, user_id)

    def fetch_chat_history(self, conversation_id: int, user_id: int) -> list[dict]:
        """Fucntion fetches messages beetween user and LLM from DB

        Args:
            conversation_id (int):
            user_id (int):

        Returns:
            list[dict]: User - Bot messages
        """

        chat_history_sql: list[Messages] = self.db.chat_history(
            conversation_id=conversation_id, user_id=user_id
        )

        chat_history = []
        for message in chat_history_sql:
            chat_history.append(Message.model_validate(message).model_dump())

        return chat_history

    def create_conversation(self, user_id: int) -> int:
        """Function creates new conversation on behalf od User with User ID, saves it to DB and returns conversation ID so frontend can attach new messages to it

        Args:
            user_id (int): user ID

        Returns:
            int: Conversation ID
        """
        return self.db.create_conversation(user_id)

    def show_avaliable_models(
        self,
    ):
        return self.chat_bot_client.show_avaliable_models()

    def validate_conversation_access(self, conversation_id: int, user_id: int):
        """Validate that the conversation exists and belongs to the user.

        This method delegates the ownership check to the repository. It does not
        return anything. If the conversation does not exist or is not owned by the
        given user, the repository raises DataBaseResourceNotFound.

        Args:
            conversation_id (int): ID of the conversation being accessed.
            user_id (int): ID of the user requesting access.
        """
        self.db.validate_conversation_access(
            conversation_id=conversation_id, user_id=user_id
        )

    # !RAG  ==================================================
    @traceable(name="RAG-CHAT")
    def rag_streaming_response(
        self,
        model: str,
        temperature: float,
        top_k,
        top_p,
        num_ctx,
        num_predict,
        repeat_penalty,
        is_thinking,
        user_id: int,
        chat_history: list[dict],
        question: str,
        conversation_id: int,
    ):
        """Generate a streaming RAG response using conversation history and user-specific documents.

        Args:
            model (str): Name of the Ollama model to use.
            temperature (float): Controls the randomness of generated responses.
            top_k (int): Number of candidate tokens considered during sampling.
            top_p (float): Cumulative probability threshold for token sampling.
            num_ctx (int): Maximum context window size in tokens.
            num_predict (int): Maximum number of tokens to generate.
            repeat_penalty (float): Penalty applied to repeated tokens.
            is_thinking (bool): Enables reasoning mode for supported models.
            user_id (int): User ID used to filter documents in the vector store.
            chat_history (list[dict]): Previous conversation messages used to
                contextualize the question and generate the response.
            question (str): Current user question.
            conversation_id (int): Conversation ID used to save the generated response.

        Yields:
            str: Generated response chunks or an error message if Ollama fails.

        Notes:
            Uses a history-aware retriever to retrieve relevant documents filtered
            by user ID. Streams the generated answer and attempts to save the
            complete response to the database after successful generation.
            Ollama errors are logged and returned as streamed error messages.
            Database persistence errors are logged without interrupting the response.
        """

        llm = self.chat_bot_client.get_llm(
            model=model,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            num_ctx=num_ctx,
            num_predict=num_predict,
            repeat_penalty=repeat_penalty,
            is_thinking=is_thinking,
        )

        retriver = self.vector_storage.return_retiver(
            serach_kwargs={"k": 3, "filter": {"user_id": user_id}}
        )
        # Enrich question based on user chat history

        system_instruction = """Given a chat history and the latest user question \
        which might reference context in the chat history, formulate a standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate it if needed and otherwise return it as is."""

        prompt_question_contextualize = ChatPromptTemplate.from_messages(
            [
                ("system", system_instruction),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        contextualized_retrived_docs = create_history_aware_retriever(
            llm, retriver, prompt_question_contextualize
        )

        # RAG
        qa_system_prompt = """You are an assistant for          question-answering tasks. \
            Use the following pieces of retrieved context to answer the question. \
            If you don't know the answer, just say that you don't know. \


            {context}"""

        prompt_answer_question = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        question_answer_chain = create_stuff_documents_chain(
            llm, prompt_answer_question
        )

        rag_chain = create_retrieval_chain(
            contextualized_retrived_docs, question_answer_chain
        )

        full_llm_response = ""
        try:
            for chunk in rag_chain.stream(
                {"input": question, "chat_history": chat_history}
            ):
                if "answer" in chunk:
                    answer_chunk = chunk["answer"]
                    full_llm_response += answer_chunk
                    yield answer_chunk

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

        try:
            self.db.save_bot_output(
                output=full_llm_response,
                conversation_id=conversation_id,
                user_id=user_id,
            )

        except DataBaseResourceNotFound:
            logger.exception(
                f"Can not save LLM output. Conversation disappeared or access invalid after streaming Conversation_ID: {conversation_id} User_ID: {user_id}"
            )
        except DataBaseError:
            logger.exception(
                f"Can not save LLM output. Failed to save bot output after streaming response Conversation_ID: {conversation_id} User_ID: {user_id}"
            )

    #! Thread Save response
    def thread_safe_rag_streaming_response(
        self,
        model: str,
        temperature: float,
        top_k,
        top_p,
        num_ctx,
        num_predict,
        repeat_penalty,
        is_thinking,
        user_id: int,
        chat_history: list[dict],
        question: str,
        conversation_id: int,
        lock_object: Lock,
    ):
        """Stream a RAG response while holding a conversation-specific thread lock.

        Wraps the RAG response generator to ensure that the conversation lock
        remains acquired throughout the entire streaming process.

        The wrapper iterates over the underlying RAG generator and yields each
        response chunk to the client. The lock is released in the finally block
        when streaming finishes, raises an exception, or the generator is closed.

        This prevents concurrent requests from processing the same conversation
        while a response is being generated.


        Yields:
            str: Response chunks generated by the underlying RAG pipeline.

        Notes:
            The finally block releases the lock when the wrapper generator
            terminates or is explicitly closed. If the generator is never started,
            its finally block will not execute.
        """

        try:
            for chunk in self.rag_streaming_response(
                model=model,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                num_ctx=num_ctx,
                num_predict=num_predict,
                repeat_penalty=repeat_penalty,
                is_thinking=is_thinking,
                user_id=user_id,
                chat_history=chat_history,
                question=question,
                conversation_id=conversation_id,
            ):
                yield chunk

        finally:
            #! realase LOCK after streaming
            lock_object.release()
