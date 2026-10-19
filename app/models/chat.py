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
    result: Any | None = None
    error: str | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Tokens used by prompt context (system + history + message + tools)")
    completion_tokens: int = Field(default=0, description="Tokens generated in the completion")
    total_tokens: int = Field(default=0, description="Total tokens used in the current context window")
    context_window_limit: int = Field(default=128000, description="Total context window token capacity for the model")
    context_window_used_pct: float = Field(default=0.0, description="Percentage of context window capacity utilized")
    cumulative_total_tokens: int | None = Field(default=None, description="Sum of total tokens across all iterations for this prompt")


class IterationStep(BaseModel):
    iteration: int
    thought: str | None = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    token_usage: TokenUsage | None = Field(default=None, description="Token usage for this iteration")


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
    iterations: list[IterationStep] = Field(default_factory=list)
    token_usage: TokenUsage | None = Field(default=None, description="Context window token usage details")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
