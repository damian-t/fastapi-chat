from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ToolCallRecord(BaseModel):
    tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, examples=["What open RFQs are in SLD?"])
    history: list[ChatMessage] = Field(default_factory=list)
    mode: str | None = Field(
        default=None,
        description="Execution mode: 'mock' (default) or 'gemini' (Gemini 3.8 Flash)",
        examples=["mock", "gemini"],
    )


class ChatResponse(BaseModel):
    reply: str
    model: str = Field(..., examples=["sld-assistant-dummy-v1", "gemini-3.8-flash"])
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
