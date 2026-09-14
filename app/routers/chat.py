from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.llm_service import dummy_llm_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    reply = await dummy_llm_service.generate_reply(
        message=payload.message,
        history=payload.history,
    )
    return ChatResponse(reply=reply, model=dummy_llm_service.model_name)
