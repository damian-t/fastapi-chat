import json
import os
from typing import Any
from app.models.chat import ChatMessage, ToolCallRecord
from app.services.llm_client import (
    BaseLLMClient,
    MockLLMClient,
    GeminiLLMClient,
    mock_llm_client,
    gemini_llm_client,
)
from app.services.sld_service import sld_service

# Tool descriptions provided to the LLM
SLD_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_rfqs",
            "description": "Fetch structured product RFQs from SLD with optional filters for status, currency, issuer, product type, or specific RFQ ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rfq_id": {"type": "string", "description": "Specific RFQ ID or ISIN (e.g. 'RFQ-101')"},
                    "status": {
                        "type": "string",
                        "enum": ["open", "quoted", "traded", "expired", "rejected"],
                        "description": "Lifecycle status of the RFQ",
                    },
                    "currency": {"type": "string", "description": "Currency code (e.g. CHF, USD, EUR)"},
                    "issuer": {"type": "string", "description": "Quoted or traded issuer bank (e.g. ZKB, UBS, Vontobel, BNP Paribas)"},
                    "product_type": {"type": "string", "description": "Product type (e.g. 'Barrier Reverse Convertible', 'Autocallable')"},
                    "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_underlyings_of_product",
            "description": "Fetch underlying basket constituents, strike levels, spot prices, current prices, barrier levels, and breach status for a product or RFQ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID (e.g. 'PRD-101'), ISIN ('CH1261564201'), or RFQ ID ('RFQ-101')"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fees_of_product",
            "description": "Fetch the fee schedule (distribution fee, structuring fee, management fee, exchange fee, total fee % and monetary amount) for a product or RFQ.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID (e.g. 'PRD-101'), ISIN ('CH1261564201'), or RFQ ID ('RFQ-101')"},
                    "fee_type": {"type": "string", "description": "Optional fee category filter (e.g. 'distribution', 'structuring', 'all')"},
                },
                "required": ["product_id"],
            },
        },
    },
]

GEMINI_PROMPT_CONTEXT = """You are the SLD Structured Products Assistant. You distribute and answer inquiries about Requests for Quotes (RFQs), underlying basket performance, and fee schedules for structured products in the SLD application.

You have access to 3 tools in your context:

1. get_rfqs(rfq_id=None, status=None, currency=None, issuer=None, product_type=None, limit=10)
   Description: Fetch structured product RFQs from SLD with optional filters for status ('open', 'quoted', 'traded', 'expired', 'rejected'), currency (e.g. 'CHF', 'USD', 'EUR'), issuer (e.g. 'ZKB', 'UBS', 'Vontobel', 'BNP Paribas'), product type ('Barrier Reverse Convertible', 'Autocallable'), or specific RFQ ID.

2. get_underlyings_of_product(product_id)
   Description: Fetch underlying basket constituents, strike levels, spot prices, current prices, barrier levels, and breach status for a product or RFQ.
   Parameters:
     - product_id: Product ID (e.g. 'PRD-101'), ISIN (e.g. 'CH1261564201'), or RFQ ID (e.g. 'RFQ-101') (REQUIRED)

3. get_fees_of_product(product_id, fee_type=None)
   Description: Fetch the fee schedule (distribution fee, structuring fee, management fee, exchange fee, total fee % and monetary amount) for a product or RFQ.
   Parameters:
     - product_id: Product ID (e.g. 'PRD-101'), ISIN (e.g. 'CH1261564201'), or RFQ ID (e.g. 'RFQ-101') (REQUIRED)
     - fee_type: Optional fee category ('distribution', 'structuring', 'all')

INSTRUCTIONS:
- Evaluate the user query. Determine which tools to call and with what parameters.
- If you need to call tools, respond ONLY with a JSON block in this format:
```json
{
  "tool_calls": [
    {
      "name": "tool_name",
      "arguments": {"param1": "value1"}
    }
  ]
}
```
- If you have sufficient information to answer the user query (or for general greetings/help), provide a clear, professional, and comprehensive final response answering the question and interpreting any financial results in markdown. Do NOT output a tool_calls JSON block when providing your final response.
"""

TOOL_RUNNERS = {
    "get_rfqs": lambda args: [r.model_dump() for r in sld_service.get_rfqs(**args)],
    "get_products": lambda args: [p.model_dump() for p in sld_service.get_products(**args)],
    "get_underlyings_of_product": lambda args: sld_service.get_underlyings_of_product(**args).model_dump(),
    "get_fees_of_product": lambda args: sld_service.get_fees_of_product(**args).model_dump(),
}


class LLMService:
    """Iterative tool-calling agent service.
    
    1. Sends the user query and tool descriptions to the LLM.
    2. The LLM determines which calls to make in which order with which arguments.
    3. The backend executes the API calls instructed by the LLM.
    4. The results are returned to the LLM together with the user query.
    5. If sufficient to answer, the LLM responds with the interpretation.
       Otherwise, it instructs the backend to make additional calls until complete.
    """

    def __init__(self, llm_client: BaseLLMClient | None = None, max_iterations: int = 5) -> None:
        self.llm_client = llm_client or mock_llm_client
        self.max_iterations = max_iterations

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    async def execute_and_interpret(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> tuple[str, list[ToolCallRecord]]:
        is_prompt_only = getattr(self.llm_client, "is_prompt_only", False)

        # 1. Prepare initial conversation
        if is_prompt_only:
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": GEMINI_PROMPT_CONTEXT}
            ]
        else:
            messages: list[dict[str, Any]] = [
                {
                    "role": "system",
                    "content": (
                        "You are the SLD Structured Products Assistant. You distribute and answer inquiries about RFQs, "
                        "underlying assets, and fee schedules for structured products in the SLD application. "
                        "Determine which tools to call with which arguments. When the backend provides the results, "
                        "evaluate if you have sufficient information to answer the user query. "
                        "If sufficient, return the final interpretation. Otherwise, instruct the backend to make additional calls."
                    ),
                }
            ]

        for item in (history or []):
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": message.strip()})

        records: list[ToolCallRecord] = []
        iteration = 0

        # Iterative loop: continue until LLM deems results sufficient or max_iterations reached
        while iteration < self.max_iterations:
            iteration += 1

            # Give tool descriptions and current context to the LLM
            tools_spec = None if is_prompt_only else SLD_TOOLS
            llm_decision = await self.llm_client.query(messages=messages, tools=tools_spec)

            # If LLM decides it has sufficient information (no more tool calls), finish!
            if not llm_decision.tool_calls:
                final_content = llm_decision.content or ""
                header_blocks = []
                if records:
                    call_summaries = []
                    for rec in records:
                        param_strs = [f"{k}={v!r}" for k, v in rec.parameters.items() if v is not None]
                        call_summaries.append(f"`{rec.tool}({', '.join(param_strs)})`")
                    header_blocks.append(f"🔧 **Tools Called ({len(records)}):** {' → '.join(call_summaries)}\n")

                if header_blocks and not final_content.startswith("🔧"):
                    final_content = f"{header_blocks[0]}\n---\n\n{final_content}"

                return final_content, records

            # The LLM instructed the backend to call one or more tools
            if is_prompt_only:
                messages.append({
                    "role": "assistant",
                    "content": llm_decision.content or json.dumps({"tool_calls": [tc.model_dump() for tc in llm_decision.tool_calls]}),
                })
                
                tool_results_texts: list[str] = []
                for tc in llm_decision.tool_calls:
                    runner = TOOL_RUNNERS.get(tc.name)
                    if not runner:
                        err_msg = {"error": f"Tool '{tc.name}' not found"}
                        tool_results_texts.append(f"- Tool: {tc.name}\n  Error: Tool not found")
                        records.append(
                            ToolCallRecord(
                                tool=tc.name,
                                parameters=tc.arguments,
                                summary=f"Tool '{tc.name}' not found",
                            )
                        )
                        continue

                    try:
                        tool_output = runner(tc.arguments)
                        tool_results_texts.append(
                            f"- Tool: {tc.name}\n"
                            f"  Arguments: {json.dumps(tc.arguments)}\n"
                            f"  Result: {json.dumps(tool_output)}"
                        )
                        records.append(
                            ToolCallRecord(
                                tool=tc.name,
                                parameters=tc.arguments,
                                summary=f"Executed {tc.name}",
                            )
                        )
                    except Exception as exc:
                        tool_results_texts.append(
                            f"- Tool: {tc.name}\n"
                            f"  Arguments: {json.dumps(tc.arguments)}\n"
                            f"  Error: {str(exc)}"
                        )
                        records.append(
                            ToolCallRecord(
                                tool=tc.name,
                                parameters=tc.arguments,
                                summary=f"Failed: {exc}",
                            )
                        )

                # Return results back to the LLM together with the user query
                messages.append({
                    "role": "user",
                    "content": (
                        f'Original user query: "{message.strip()}"\n\n'
                        f"Tool execution results:\n"
                        + "\n".join(tool_results_texts)
                        + "\n\nBased on these results and the user query, determine if you need further tool calls, or provide the final answer and interpretation."
                    ),
                })

            else:
                # Role-based tool response for Mock LLM client
                messages.append({
                    "role": "assistant",
                    "content": llm_decision.content,
                    "tool_calls": [tc.model_dump() for tc in llm_decision.tool_calls],
                })

                # Backend executes the tool calls as instructed by the LLM
                for tc in llm_decision.tool_calls:
                    runner = TOOL_RUNNERS.get(tc.name)
                    if not runner:
                        err_msg = {"error": f"Tool '{tc.name}' not found"}
                        messages.append({"role": "tool", "name": tc.name, "content": json.dumps(err_msg)})
                        continue

                    try:
                        tool_output = runner(tc.arguments)
                        messages.append({"role": "tool", "name": tc.name, "content": json.dumps(tool_output)})
                        records.append(
                            ToolCallRecord(
                                tool=tc.name,
                                parameters=tc.arguments,
                                summary=f"Executed {tc.name}",
                            )
                        )
                    except Exception as exc:
                        err_output = {"error": str(exc)}
                        messages.append({"role": "tool", "name": tc.name, "content": json.dumps(err_output)})
                        records.append(
                            ToolCallRecord(
                                tool=tc.name,
                                parameters=tc.arguments,
                                summary=f"Failed: {exc}",
                            )
                        )

        # Fallback interpretation if max iterations reached
        if is_prompt_only:
            messages.append({
                "role": "user",
                "content": (
                    f'Original user query: "{message.strip()}". '
                    "Maximum iterations reached. Please provide your best final answer and financial interpretation based on the information gathered so far."
                ),
            })
            fallback_response = await self.llm_client.query(messages=messages, tools=None)
        else:
            fallback_response = await self.llm_client.query(messages=messages, tools=None)

        return fallback_response.content or "Completed with maximum iterations reached.", records

    async def generate_reply(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> str:
        reply, _ = await self.execute_and_interpret(message=message, history=history)
        return reply


dummy_llm_service = LLMService(llm_client=mock_llm_client)
gemini_llm_service = LLMService(llm_client=gemini_llm_client)


def get_llm_service(mode: str | None = None) -> LLMService:
    """Retrieve LLM service for the requested mode ('mock' or 'gemini')."""
    selected = (mode or os.getenv("LLM_MODE", "mock")).lower().strip()
    if selected in ("gemini", "gemini-3.8-flash", "live"):
        return gemini_llm_service
    return dummy_llm_service
