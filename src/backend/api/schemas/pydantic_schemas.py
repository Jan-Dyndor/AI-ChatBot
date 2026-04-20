from typing import Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["assistant", "user"]
    content: str


class UserInput(BaseModel):
    input: str = Field(min_length=1, max_length=3000)
    model: Literal["llama3:8b"]
    chat_history: list[ChatMessage]
