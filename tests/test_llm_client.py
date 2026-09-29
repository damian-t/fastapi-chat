import pytest
from app.services.llm_client import MockLLMClient, LLMToolCall, LLMResponse
from app.services.llm_service import LLMService, SLD_TOOLS


@pytest.mark.asyncio
async def test_mock_llm_client_greeting():
    client = MockLLMClient()
    res = await client.query(messages=[{"role": "user", "content": "Hi"}], tools=SLD_TOOLS)
    assert res.content is not None
    assert "SLD Structured Products Assistant" in res.content
    assert len(res.tool_calls) == 0


@pytest.mark.asyncio
async def test_mock_llm_client_tool_selection():
    client = MockLLMClient()
    res = await client.query(
        messages=[{"role": "user", "content": "Show all open RFQs in USD"}],
        tools=SLD_TOOLS,
    )
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "get_rfqs"
    assert res.tool_calls[0].arguments == {"status": "open", "currency": "USD"}


@pytest.mark.asyncio
async def test_multi_step_iterative_calls_until_sufficient():
    """Test iterative loop:
    1. LLM requests RFQ discovery first
    2. Backend executes and returns RFQ data
    3. LLM sees data not yet sufficient for fees, requests get_fees_of_product
    4. Backend executes and returns fee data
    5. LLM deems data sufficient and returns final interpretation without further calls.
    """
    service = LLMService()
    # "What are the fees for the open Swiss RFQ?" requires finding the open Swiss RFQ first, then calling get_fees_of_product
    reply, tool_calls = await service.execute_and_interpret(
        "What are the fees for the open Swiss RFQ?"
    )
    assert len(tool_calls) == 2
    tool_names = [tc.tool for tc in tool_calls]
    assert tool_names == ["get_rfqs", "get_fees_of_product"]
    assert "PRD-104" in reply or "RFQ-104" in reply
    assert "0.95%" in reply or "Distribution Fee" in reply


@pytest.mark.asyncio
async def test_custom_llm_iterative_control():
    """Test that a custom LLM can instruct multiple rounds of calls dynamically."""
    turn_counter = 0

    class MultiTurnLLM(MockLLMClient):
        async def query(self, messages, tools=None):
            nonlocal turn_counter
            tool_messages = [m for m in messages if m.get("role") == "tool"]

            if len(tool_messages) == 0 and tools:
                # Round 1: Call underlyings
                turn_counter += 1
                return LLMResponse(
                    tool_calls=[
                        LLMToolCall(name="get_underlyings_of_product", arguments={"product_id": "RFQ-101"})
                    ]
                )
            elif len(tool_messages) == 1 and tools:
                # Round 2: Not sufficient yet, call fees
                turn_counter += 1
                return LLMResponse(
                    tool_calls=[
                        LLMToolCall(name="get_fees_of_product", arguments={"product_id": "RFQ-101"})
                    ]
                )
            else:
                # Round 3: Sufficient! Return interpretation
                turn_counter += 1
                return LLMResponse(content="Both underlyings and fees have been gathered and interpreted.")

    custom_service = LLMService(llm_client=MultiTurnLLM())
    reply, tool_calls = await custom_service.execute_and_interpret("Analyze RFQ-101 fully")
    assert len(tool_calls) == 2
    assert tool_calls[0].tool == "get_underlyings_of_product"
    assert tool_calls[1].tool == "get_fees_of_product"
    assert "Both underlyings and fees have been gathered and interpreted." in reply
    assert turn_counter == 3
