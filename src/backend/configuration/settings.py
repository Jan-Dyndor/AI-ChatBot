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

    model_config = SettingsConfigDict(
        env_file=root / ".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings(env_file_location: str | Path | None = None) -> Settings:
    if not env_file_location:
        load_dotenv()  # to load env file to LangSmith lib
        return Settings()  # type: ignore
    else:
        load_dotenv(dotenv_path=env_file_location)  # to load env file to LangSmith lib
        return Settings(_env_file=env_file_location, _env_file_encoding="utf-8")  # type: ignore
