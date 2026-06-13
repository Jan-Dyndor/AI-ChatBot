from functools import lru_cache
from pathlib import Path

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

    model_config = SettingsConfigDict(
        env_file=root / ".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
