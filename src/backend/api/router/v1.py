from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from time import sleep
from backend.chat_bot.client import ai_bot

router = APIRouter(prefix="/v1", tags=["v1"])


def fake_video_streamer():
    for i in range(10):
        yield "some fake video bytes"
        sleep(1)


@router.get("/")
def health():
    return {"status": "ok"}


@router.post("/chat")
def chat(input):
    return StreamingResponse(ai_bot.stream_response(input), media_type="text/plain")
