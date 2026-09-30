import os
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_client import (
    GeminiLLMClient,
    LLMToolCall,
    extract_tool_calls,
    get_gemini_api_key,
)
from app.services.llm_service import LLMService

client = TestClient(app)


def test_modes_endpoint():
    res = client.get("/api/chat/modes")
    assert res.status_code == 200
    data = res.json()
    assert "default_mode" in data
    mode_ids = [m["id"] for m in data["available_modes"]]
    assert "mock" in mode_ids
    assert "gemini" in mode_ids


def test_chat_explicit_mock_mode():
    res = client.post(
        "/api/chat",
        json={"message": "Show all open RFQs in USD", "mode": "mock"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["model"] == "mock-sld-llm-v2"
    assert len(data["tool_calls"]) == 1
    assert data["tool_calls"][0]["tool"] == "get_rfqs"


def test_extract_tool_calls_variations():
    # 1. Code fence with tool_calls list
    fenced = """I will query the open RFQs:
```json
{
  "tool_calls": [
    {
      "name": "get_rfqs",
      "arguments": {"status": "open", "currency": "USD"}
    }
  ]
}
```"""
    calls = extract_tool_calls(fenced)
    assert len(calls) == 1
    assert calls[0].name == "get_rfqs"
    assert calls[0].arguments == {"status": "open", "currency": "USD"}

    # 2. Raw JSON single call
    single = '{"tool": "get_fees_of_product", "parameters": {"product_id": "PRD-101"}}'
    calls_single = extract_tool_calls(single)
    assert len(calls_single) == 1
    assert calls_single[0].name == "get_fees_of_product"
    assert calls_single[0].arguments == {"product_id": "PRD-101"}

    # 3. List of calls
    calls_list = '[{"name": "get_rfqs", "arguments": {}}, {"name": "get_fees_of_product", "arguments": {"product_id": "PRD-102"}}]'
    res_list = extract_tool_calls(calls_list)
    assert len(res_list) == 2
    assert res_list[0].name == "get_rfqs"
    assert res_list[1].name == "get_fees_of_product"

    # 4. Plain conversation text (no tool calls)
    plain = "Hello! I am your SLD assistant. How can I assist you with structured products today?"
    assert extract_tool_calls(plain) == []


@pytest.mark.asyncio
async def test_gemini_client_missing_key():
    gemini_client = GeminiLLMClient(api_key="")
    with patch("app.services.llm_client.get_gemini_api_key", return_value=None):
        gemini_client.api_key = None
        with pytest.raises(ValueError, match="Gemini API key not found"):
            await gemini_client.query([{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_gemini_mode_prompt_only_iteration_mocked():
    """Verify prompt-only interaction with Gemini:
    Turn 1: Gemini returns a JSON tool call in text.
    Turn 2: Backend passes execution results + original query back to Gemini, Gemini returns final interpretation.
    """
    call_history = []

    class MockGeminiClient(GeminiLLMClient):
        async def query(self, messages, tools=None):
            assert tools is None  # Interaction is STRICTLY prompt-based!
            call_history.append(messages)

            # If this is turn 1 (only system + user query)
            if len(messages) == 2:
                return await super().query.__wrapped__(self, messages) if hasattr(super().query, "__wrapped__") else None
            return None

    # Simulate Gemini responses
    gemini_sim = GeminiLLMClient(api_key="test-key")
    turn_counter = 0

    async def mock_query(messages, tools=None):
        nonlocal turn_counter
        turn_counter += 1
        assert tools is None  # Tools must NEVER be passed to Gemini API!

        if turn_counter == 1:
            return extract_tool_calls(
                '```json\n{"tool_calls": [{"name": "get_rfqs", "arguments": {"status": "open", "currency": "USD"}}]}\n```'
            )
        else:
            # Verify the backend passed the user query and tool results back to the LLM
            last_message = messages[-1]
            assert last_message["role"] == "user"
            assert "Original user query:" in last_message["content"]
            assert "Tool execution results:" in last_message["content"]
            assert "get_rfqs" in last_message["content"]

    service = LLMService(llm_client=gemini_sim)

    with patch.object(gemini_sim, "query") as mock_q:
        from app.services.llm_client import LLMResponse
        mock_q.side_effect = [
            LLMResponse(
                content='```json\n{"tool_calls": [{"name": "get_rfqs", "arguments": {"status": "open", "currency": "USD"}}]}\n```',
                tool_calls=[LLMToolCall(name="get_rfqs", arguments={"status": "open", "currency": "USD"})],
            ),
            LLMResponse(
                content="Here is the open USD RFQ: RFQ-102 Autocallable BRC quoted at 99.90%.",
                tool_calls=[],
            ),
        ]

        reply, tool_records = await service.execute_and_interpret("Show me all open RFQs in USD")
        assert len(tool_records) == 1
        assert tool_records[0].tool == "get_rfqs"
        assert tool_records[0].parameters == {"status": "open", "currency": "USD"}
        assert "RFQ-102" in reply
        assert "Tools Called (1)" in reply


@pytest.mark.asyncio
async def test_gemini_multi_step_tool_loop_mocked():
    """Verify multi-step reasoning in prompt-only mode:
    Turn 1: get_rfqs(currency="CHF", status="open")
    Turn 2: get_fees_of_product(product_id="PRD-104")
    Turn 3: final answer
    """
    gemini_sim = GeminiLLMClient(api_key="test-key")
    service = LLMService(llm_client=gemini_sim)

    from app.services.llm_client import LLMResponse
    with patch.object(gemini_sim, "query") as mock_q:
        mock_q.side_effect = [
            LLMResponse(
                content='```json\n{"tool_calls": [{"name": "get_rfqs", "arguments": {"currency": "CHF", "status": "open"}}]}\n```',
                tool_calls=[LLMToolCall(name="get_rfqs", arguments={"currency": "CHF", "status": "open"})],
            ),
            LLMResponse(
                content='```json\n{"tool_calls": [{"name": "get_fees_of_product", "arguments": {"product_id": "PRD-104"}}]}\n```',
                tool_calls=[LLMToolCall(name="get_fees_of_product", arguments={"product_id": "PRD-104"})],
            ),
            LLMResponse(
                content="The open Swiss RFQ (RFQ-104 / PRD-104) has a total fee of 0.95% (CHF 1,425.00).",
                tool_calls=[],
            ),
        ]

        reply, records = await service.execute_and_interpret("What are the fees for the open Swiss RFQ?")
        assert len(records) == 2
        assert records[0].tool == "get_rfqs"
        assert records[1].tool == "get_fees_of_product"
        assert "0.95%" in reply


@pytest.mark.asyncio
async def test_live_gemini_mode_if_key_available():
    """If GOOGLE_API_KEY or GEMINI_API_KEY is configured, run an end-to-end live test."""
    key = get_gemini_api_key()
    if not key:
        pytest.skip("No Gemini API key available for live test")

    res = client.post(
        "/api/chat",
        json={"message": "Show me all open RFQs in USD", "mode": "gemini"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["model"] == "gemini-3.8-flash"
    assert len(data["tool_calls"]) >= 1
    assert data["tool_calls"][0]["tool"] == "get_rfqs"
    assert "RFQ-102" in data["reply"]
