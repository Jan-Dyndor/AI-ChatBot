from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, EmailStr


class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: Literal["assistant", "user"]
    content: str


class UserInput(BaseModel):
    input: str = Field(min_length=1, max_length=3000)
    model: Literal["llama3:8b"]
    chat_history: list[ChatMessage]
    conversation_id: int


class CreateUserRequest(BaseModel):
    email: EmailStr = Field(max_length=100)
    password: str = Field(max_length=100)


class CreateUserResponse(BaseModel):
    user_email: str
