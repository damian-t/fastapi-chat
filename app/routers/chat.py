import os
from typing import Any
from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.services.llm_client import get_gemini_api_key
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/modes")
def get_chat_modes() -> dict[str, Any]:
    """Return available LLM modes and active configuration."""
    default_mode = os.getenv("LLM_MODE", "mock").lower()
    has_gemini_key = bool(get_gemini_api_key())
    return {
        "default_mode": default_mode,
        "available_modes": [
            {
                "id": "mock",
                "name": "Mock LLM",
                "model": "mock-sld-llm-v2",
                "description": "Simulated multi-turn reasoning agent for structured products",
                "configured": True,
            },
            {
                "id": "gemini",
                "name": "Gemini 3.8 Flash",
                "model": "gemini-3.8-flash",
                "description": "Google Gemini 3.8 Flash with prompt-only tool reasoning",
                "configured": has_gemini_key,
            },
        ],
    }


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Process a chat inquiry with the selected LLM mode (mock or gemini)."""
    try:
        service = get_llm_service(payload.mode)
        reply, tool_calls, iterations = await service.execute_and_interpret(
            message=payload.message,
            history=payload.history,
            return_iterations=True,
        )
        return ChatResponse(
            reply=reply,
            model=service.model_name,
            tool_calls=tool_calls,
            iterations=iterations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
