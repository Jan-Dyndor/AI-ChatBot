from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

root = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    api_url_ai_chat: str = Field(validation_alias="API_URL")

    model_config = SettingsConfigDict(
        env_file=root / ".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type:ignore
