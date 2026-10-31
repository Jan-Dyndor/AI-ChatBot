from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

root = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    api_url_ai_chat: str = Field(validation_alias="API_URL")
    api_url_chat_history: str = Field(validation_alias="API_CHAT_HISTORY_URL")
    db_url: str = Field(validation_alias="DB_URL")
    api_url_create_conversation: str = Field(
        validation_alias="API_CREATE_CONVERSATION_URL"
    )
    api_url_latest_conversations_ids: str = Field(
        validation_alias="API_LATEST_CONVERSATIONS_IDS_URL"
    )
    api_token_url: str = Field(validation_alias="API_TOKEN_URL")
    api_create_user_url: str = Field(validation_alias="API_CREATE_USER")
    api_upload_file_url: str = Field(validation_alias="API_UPLOAD_FILE_URL")
    api_files_url: str = Field(
        validation_alias="API_FILES_URL",
    )
    api_conversations_url: str = Field(validation_alias="API_CONVERSATIONS")
    api_conversations_url_by_ID_part: str = Field(
        validation_alias="API_CONVERSATIONS_BY_ID_PART"
    )
    api_models: str = Field(validation_alias="API_MODELS")
    ollama_url: str = Field(validation_alias="OLLAMA_API")

    secret_key_jwt: str = Field(validation_alias="SECRET_KEY")
    algorythm_jwt: str = Field(validation_alias="ALGORITHM")
    token_expires_minutes: int = Field(validation_alias="JWT_EXPIRES_TIME_MINUTES")

    langsmit_api: str = Field(validation_alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(validation_alias="LANGSMITH_PROJECT")
    langsmith_tracing: bool = Field(validation_alias="LANGSMITH_TRACING")
    langsmith_endpoit: str = Field(validation_alias="LANGSMITH_ENDPOINT")

    max_file_size_BYTES: int = Field(
        validation_alias="MAX_FILE_SIZE_BYTES", default=10485760
    )  # 10 MB
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=50)
    embedding_model: str = Field(validation_alias="EMBEDDING_MODEL")
    collection_name_vector_store: str = Field(default="AI_chat_bot_collection")
    chroma_db_host: str = Field(validation_alias="CHROMA_DB_HOST")
    chroma_db_port: int = Field(validation_alias="CHROMA_DB_PORT")

    # TEST RAG EVALS
    test_deepevals_model: str = Field(
        default="llama3:8b", validation_alias="TEST_DEEPEVALS_MODEL"
    )
    test_deepevals_temp: int = Field(default=0, validation_alias="TEST_DEEPEVALS_TEMP")
    test_deepevals_top_k: int = Field(
        default=40, validation_alias="TEST_DEEPEVALS_TOP_K"
    )
    test_deepevals_top_p: float = Field(
        default=0.9, validation_alias="TEST_DEEPEVALS_TOP_P"
    )
    test_deepevals_num_ctx: int = Field(
        default=4096, validation_alias="TEST_DEEPEVALS_NUM_CTX"
    )
    test_deepevals_temp_num_predict: int = Field(
        default=300, validation_alias="TEST_DEEPEVALS_NUM_PREDICT"
    )
    test_deepevals_repeat_penalty: float = Field(
        default=1.1, validation_alias="TEST_DEEPEVALS_REPEAT_PENALTY"
    )
    test_deepevals_is_thinking: bool = Field(
        default=False, validation_alias="TEST_DEEPEVALS_IS_THINKING"
    )

    model_config = SettingsConfigDict(
        env_file=root / ".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings(env_file_location: str | Path | None = None) -> Settings:
    if not env_file_location:
        load_dotenv()  # to load env file to LangSmith lib
        return Settings()  # type: ignore
    else:
        # Explicit env files (used by tests) must override variables loaded earlier.
        load_dotenv(dotenv_path=env_file_location, override=True)
        return Settings(_env_file=env_file_location, _env_file_encoding="utf-8")  # type: ignore
