from pydantic import BaseModel, Field


class UserInput(BaseModel):
    input: str = Field(min_length=1, max_length=3000)
