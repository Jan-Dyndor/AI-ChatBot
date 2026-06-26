from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: Literal["assistant", "user"]
    content: str


class ModelParameters(BaseModel):

    temperature: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Controls randomness. Lower = more focused, higher = more creative.",
    )

    top_k: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Limits token selection to the K most likely tokens. Lower = more conservative.",
    )

    top_p: float = Field(
        default=0.9,
        ge=0,
        le=1,
        description="Nucleus sampling. Lower = more focused, higher = more diverse.",
    )

    num_ctx: int = Field(
        default=4096,
        ge=512,
        le=8192,
        description="Context window size in tokens. Controls how much text the model can consider.",
    )

    num_predict: int = Field(
        default=300,
        ge=1,
        le=2000,
        description="Maximum number of tokens the model is allowed to generate.",
    )

    repeat_penalty: float = Field(
        default=1.1,
        ge=0.8,
        le=2.0,
        description="Penalizes repeated text. Higher values reduce repetition more strongly.",
    )


class UserInput(BaseModel):
    input: str = Field(min_length=1, max_length=3000)
    model: Literal["llama3:8b"]
    chat_history: list[ChatMessage]
    conversation_id: int
    model_parameters: ModelParameters


class CreateUserRequest(BaseModel):
    email: EmailStr = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=100)


class CreateUserResponse(BaseModel):
    email: EmailStr


class UserLogin(BaseModel):
    email: EmailStr = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str


class UserDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    password_hash: str
