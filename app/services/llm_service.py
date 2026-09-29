import json
from typing import Any
from app.models.chat import ChatMessage, ToolCallRecord
from app.services.llm_client import MockLLMClient, mock_llm_client
from app.services.sld_service import sld_service

# Declarations of tools available to the LLM
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

TOOL_RUNNERS = {
    "get_rfqs": lambda args: [r.model_dump() for r in sld_service.get_rfqs(**args)],
    "get_underlyings_of_product": lambda args: sld_service.get_underlyings_of_product(**args).model_dump(),
    "get_fees_of_product": lambda args: sld_service.get_fees_of_product(**args).model_dump(),
}


class LLMService:
    """Agent service that queries an LLM client to determine tool selection,
    executes requested SLD tools, and queries the LLM to interpret the output.
    """

    def __init__(self, llm_client: MockLLMClient | None = None) -> None:
        self.llm_client = llm_client or mock_llm_client

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    async def execute_and_interpret(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> tuple[str, list[ToolCallRecord]]:
        # 1. Build messages with system instructions and conversation history
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are the SLD Structured Products Assistant. You answer questions about "
                    "RFQs, underlying assets, and fees for structured products in the SLD application. "
                    "Use the available tools whenever real-time data is needed."
                ),
            }
        ]
        for item in (history or []):
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": message.strip()})

        # 2. Query the LLM to determine which tools to run with what parameters
        llm_decision = await self.llm_client.query(messages=messages, tools=SLD_TOOLS)

        # If the LLM did not request any tools, return its conversational answer directly
        if not llm_decision.tool_calls:
            return llm_decision.content or "", []

        # 3. Execute the tools chosen by the LLM
        records: list[ToolCallRecord] = []
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [tc.model_dump() for tc in llm_decision.tool_calls],
        })

        for tc in llm_decision.tool_calls:
            runner = TOOL_RUNNERS.get(tc.name)
            if not runner:
                error_msg = {"error": f"Tool '{tc.name}' not found"}
                messages.append({"role": "tool", "name": tc.name, "content": json.dumps(error_msg)})
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

        # 4. Query the LLM again to interpret the tool results into a user-facing answer
        interpretation = await self.llm_client.query(messages=messages)

        # Prepend tool execution banner for user visibility
        header_blocks = []
        if records:
            call_summaries = []
            for rec in records:
                param_strs = [f"{k}={v!r}" for k, v in rec.parameters.items() if v is not None]
                call_summaries.append(f"`{rec.tool}({', '.join(param_strs)})`")
            header_blocks.append(f"🔧 **Tools Called:** {' & '.join(call_summaries)}\n")

        final_reply = "\n\n---\n\n".join(
            filter(None, [("\n".join(header_blocks) if header_blocks else None), interpretation.content])
        )

        return final_reply, records

    async def generate_reply(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> str:
        reply, _ = await self.execute_and_interpret(message=message, history=history)
        return reply


dummy_llm_service = LLMService()
