from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.schemas.pydantic_schemas import UserInput
from backend.service.chat_service import ChatService
from fastapi import Depends

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(user_input: UserInput, service: ChatService = Depends(ChatService)):
    return StreamingResponse(
        service.stream_response_from_client(
            model=user_input.model, chat_history=user_input.chat_history
        ),
        media_type="text/plain",
    )
