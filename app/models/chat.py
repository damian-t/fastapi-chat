from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, examples=["Hello, who are you?"])
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    model: str = Field(..., examples=["dummy-llm-v0"])
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
