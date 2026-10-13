import os
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_client import (
    GeminiNativeLLMClient,
    LLMToolCall,
    get_gemini_api_key,
)
from app.services.llm_service import LLMService, SLD_TOOLS

client = TestClient(app)


def test_modes_endpoint_includes_native():
    res = client.get("/api/chat/modes")
    assert res.status_code == 200
    data = res.json()
    mode_ids = [m["id"] for m in data["available_modes"]]
    assert "mock" in mode_ids
    assert "gemini" in mode_ids
    assert "gemini-native" in mode_ids


@pytest.mark.asyncio
async def test_gemini_native_client_missing_key():
    gemini_client = GeminiNativeLLMClient(api_key="")
    with patch("app.services.llm_client.get_gemini_api_key", return_value=None):
        gemini_client.api_key = None
        with pytest.raises(ValueError, match="Gemini API key not found"):
            await gemini_client.query([{"role": "user", "content": "Hi"}], tools=SLD_TOOLS)


@pytest.mark.asyncio
async def test_gemini_native_client_passes_tools_to_api():
    gemini_client = GeminiNativeLLMClient(api_key="test-api-key")
    
    mock_response_data = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "get_rfqs",
                                "arguments": json.dumps({"currency": "USD", "status": "open"}),
                            },
                        }
                    ],
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_post.return_value = mock_resp

        messages = [{"role": "user", "content": "Show USD RFQs"}]
        result = await gemini_client.query(messages=messages, tools=SLD_TOOLS)

        assert mock_post.called
        call_kwargs = mock_post.call_args.kwargs
        assert "tools" in call_kwargs["json"]
        assert call_kwargs["json"]["tools"] == SLD_TOOLS
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "get_rfqs"
        assert result.tool_calls[0].arguments == {"currency": "USD", "status": "open"}
        assert result.tool_calls[0].id == "call_123"
        assert result.raw_message is not None


@pytest.mark.asyncio
async def test_gemini_native_multi_turn_tool_loop_mocked():
    """Verify native function calling loop in LLMService:
    Turn 1: Gemini returns a native tool call for get_rfqs.
    Turn 2: Backend executes and sends role='tool' with tool_call_id, Gemini returns final interpretation.
    """
    gemini_sim = GeminiNativeLLMClient(api_key="test-key")
    service = LLMService(llm_client=gemini_sim)

    from app.services.llm_client import LLMResponse
    with patch.object(gemini_sim, "query") as mock_q:
        raw_msg_1 = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_abc_1",
                    "type": "function",
                    "function": {
                        "name": "get_rfqs",
                        "arguments": '{"currency": "USD", "status": "open"}',
                    },
                }
            ],
        }
        mock_q.side_effect = [
            LLMResponse(
                content="",
                tool_calls=[LLMToolCall(id="call_abc_1", name="get_rfqs", arguments={"currency": "USD", "status": "open"})],
                raw_message=raw_msg_1,
            ),
            LLMResponse(
                content="Found 1 open USD RFQ: RFQ-102 Autocallable BRC quoted at 99.90%.",
                tool_calls=[],
                raw_message={"role": "assistant", "content": "Found 1 open USD RFQ: RFQ-102 Autocallable BRC quoted at 99.90%."},
            ),
        ]

        reply, records, steps = await service.execute_and_interpret(
            "Show me all open RFQs in USD", return_iterations=True
        )

        assert len(records) == 1
        assert records[0].tool == "get_rfqs"
        assert records[0].parameters == {"currency": "USD", "status": "open"}
        assert "RFQ-102" in reply
        assert len(steps) == 1


@pytest.mark.asyncio
async def test_live_gemini_native_mode_if_key_available():
    """Live test using Gemini 3.8 Flash native function calling API."""
    key = get_gemini_api_key()
    if not key:
        pytest.skip("No Gemini API key available for live test")

    res = client.post(
        "/api/chat",
        json={"message": "Show me all open RFQs in USD", "mode": "gemini-native"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["model"] == "gemini-3.8-flash"
    assert len(data["tool_calls"]) >= 1
    assert data["tool_calls"][0]["tool"] == "get_rfqs"
    assert "RFQ-102" in data["reply"]
