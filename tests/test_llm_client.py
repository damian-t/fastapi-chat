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
async def test_custom_llm_injection_in_service():
    class CustomTestLLM(MockLLMClient):
        async def query(self, messages, tools=None):
            if tools:
                return LLMResponse(
                    tool_calls=[
                        LLMToolCall(name="get_fees_of_product", arguments={"product_id": "RFQ-101"})
                    ]
                )
            return LLMResponse(content="Custom LLM interpreted fees successfully.")

    custom_service = LLMService(llm_client=CustomTestLLM())
    reply, tool_calls = await custom_service.execute_and_interpret("Give me fees")
    assert len(tool_calls) == 1
    assert tool_calls[0].tool == "get_fees_of_product"
    assert "Custom LLM interpreted fees successfully" in reply
