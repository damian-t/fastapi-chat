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
async def test_gemini_native_four_turn_tool_and_interpretation_flow():
    """Verify complete 4-turn interaction loop using GeminiNativeLLMClient / service:
    Turn 1: Gemini decides to call get_rfqs -> backend executes tool against SLD data.
    Turn 2: Gemini receives RFQs, decides to call get_underlyings_of_product -> backend executes tool.
    Turn 3: Gemini receives underlyings, decides to call get_fees_of_product -> backend executes tool.
    Turn 4: Gemini receives all gathered data, determines info is sufficient, and formulates final interpretation.
    """
    from app.services.llm_service import gemini_native_llm_service
    from app.services.llm_client import LLMResponse

    call_history: list[list[dict]] = []

    t1_response = LLMResponse(
        content=None,
        tool_calls=[LLMToolCall(id="call_t1_rfq", name="get_rfqs", arguments={"currency": "CHF", "status": "open"})],
        raw_message={
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_t1_rfq",
                "type": "function",
                "function": {"name": "get_rfqs", "arguments": json.dumps({"currency": "CHF", "status": "open"})},
                "extra_content": {"google": {"thought_signature": "sig_turn_1"}}
            }]
        }
    )

    t2_response = LLMResponse(
        content=None,
        tool_calls=[LLMToolCall(id="call_t2_und", name="get_underlyings_of_product", arguments={"product_id": "PRD-104"})],
        raw_message={
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_t2_und",
                "type": "function",
                "function": {"name": "get_underlyings_of_product", "arguments": json.dumps({"product_id": "PRD-104"})},
                "extra_content": {"google": {"thought_signature": "sig_turn_2"}}
            }]
        }
    )

    t3_response = LLMResponse(
        content=None,
        tool_calls=[LLMToolCall(id="call_t3_fees", name="get_fees_of_product", arguments={"product_id": "PRD-104"})],
        raw_message={
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_t3_fees",
                "type": "function",
                "function": {"name": "get_fees_of_product", "arguments": json.dumps({"product_id": "PRD-104"})},
                "extra_content": {"google": {"thought_signature": "sig_turn_3"}}
            }]
        }
    )

    t4_final_interpretation = (
        "### Financial Analysis for RFQ-104 (PRD-104)\n\n"
        "• **Product**: 18M Barrier Reverse Convertible on ABB, Sika, and Geberit\n"
        "• **Underlying Performance**: All 3 Swiss equities are currently trading above their 65% barrier levels.\n"
        "• **Fee Structure**: Total fee is 0.95% (CHF 1,425.00), comprised of 0.50% distribution fee and 0.45% structuring fee."
    )

    t4_response = LLMResponse(
        content=t4_final_interpretation,
        tool_calls=[],
        raw_message={"role": "assistant", "content": t4_final_interpretation}
    )

    async def mock_query(messages, tools=None):
        # Tools specification must be passed on all queries in native mode
        assert tools == SLD_TOOLS
        call_history.append([dict(m) for m in messages])
        turn_num = len(call_history)
        if turn_num == 1:
            return t1_response
        elif turn_num == 2:
            return t2_response
        elif turn_num == 3:
            return t3_response
        elif turn_num == 4:
            return t4_response
        raise RuntimeError(f"Unexpected turn {turn_num}")

    with patch.object(gemini_native_llm_service.llm_client, "query", side_effect=mock_query):
        reply, records, steps = await gemini_native_llm_service.execute_and_interpret(
            "Analyze the open Swiss RFQ with underlyings and fees",
            return_iterations=True
        )

    # 1. Verify 4 LLM turns were made
    assert len(call_history) == 4

    # Turn 1: system prompt + user message
    assert len(call_history[0]) == 2
    assert call_history[0][0]["role"] == "system"
    assert call_history[0][1]["role"] == "user"

    # Turn 2: system + user + assistant (with tool_call 1) + tool result 1
    assert len(call_history[1]) == 4
    assert call_history[1][2]["role"] == "assistant"
    assert call_history[1][3]["role"] == "tool"
    assert call_history[1][3]["tool_call_id"] == "call_t1_rfq"
    assert "RFQ-104" in call_history[1][3]["content"]

    # Turn 3: ... + assistant (with tool_call 2) + tool result 2
    assert len(call_history[2]) == 6
    assert call_history[2][4]["role"] == "assistant"
    assert call_history[2][5]["role"] == "tool"
    assert call_history[2][5]["tool_call_id"] == "call_t2_und"
    assert "ABBN" in call_history[2][5]["content"]

    # Turn 4: ... + assistant (with tool_call 3) + tool result 3
    assert len(call_history[3]) == 8
    assert call_history[3][6]["role"] == "assistant"
    assert call_history[3][7]["role"] == "tool"
    assert call_history[3][7]["tool_call_id"] == "call_t3_fees"
    assert "distribution_fee_pct" in call_history[3][7]["content"]

    # 2. Verify backend recorded all 3 tool executions
    assert len(records) == 3
    assert [r.tool for r in records] == ["get_rfqs", "get_underlyings_of_product", "get_fees_of_product"]
    assert records[0].parameters == {"currency": "CHF", "status": "open"}
    assert records[1].parameters == {"product_id": "PRD-104"}
    assert records[2].parameters == {"product_id": "PRD-104"}

    # 3. Verify iteration steps recorded for inspection
    assert len(steps) == 3
    assert steps[0].iteration == 1
    assert steps[1].iteration == 2
    assert steps[2].iteration == 3

    # 4. Verify the final interpreted response contains Gemini's synthesis and tool call summaries
    assert "Tools Called (3)" in reply
    assert "Financial Analysis for RFQ-104" in reply
    assert "0.95%" in reply
    assert "ABB, Sika, and Geberit" in reply


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
