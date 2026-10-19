import json
import os
from typing import Any
from app.models.chat import ChatMessage, ToolCallRecord, IterationStep, TokenUsage
from app.services.llm_client import (
    BaseLLMClient,
    MockLLMClient,
    GeminiLLMClient,
    GeminiNativeLLMClient,
    mock_llm_client,
    gemini_llm_client,
    gemini_native_llm_client,
    build_token_usage,
)
from app.services.sld_service import sld_service

from dataclasses import asdict
from decimal import Decimal

# Tool descriptions provided to the LLM
SLD_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_rfqs",
            "description": "Fetch structured products / RFQs from SLD matching search filters. Returns bounded results with metadata (total matches, items). Use limit/offset and filters (currency, status, product_type, underlying) to query subsets and protect LLM context size.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date of search period (e.g. '2026-09-28' or ISO format YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for search period (e.g. '2026-09-29' or ISO format YYYY-MM-DD)",
                    },
                    "isin": {
                        "type": "string",
                        "description": "Security ISIN identifier of the quoted product (e.g. 'CH1261564201')",
                    },
                    "valor": {
                        "type": "string",
                        "description": "Security Valor identifier of the quoted product (e.g. '126156101')",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "quoted", "traded", "expired", "rejected"],
                        "description": "Optional lifecycle status of the product",
                    },
                    "currency": {"type": "string", "description": "Optional currency code (e.g. CHF, USD, EUR)"},
                    "issuer": {"type": "string", "description": "Optional quoted or traded issuer bank (e.g. ZKB, UBS, Vontobel, BNP Paribas)"},
                    "product_type": {"type": "string", "description": "Optional product structure type (e.g. 'Barrier Reverse Convertible', 'Autocallable')"},
                    "underlying": {"type": "string", "description": "Optional underlying ticker symbol (e.g. 'NESN', 'NOVN', 'AAPL', 'ROG SW')"},
                    "rfq_id": {"type": "string", "description": "Optional specific product ID, RFQ ID, or ISIN"},
                    "limit": {"type": "integer", "description": "Maximum number of items to return (default 10, max 50) to keep context bounded"},
                    "offset": {"type": "integer", "description": "Offset for pagination (default 0)"},
                    "compact": {"type": "boolean", "description": "Whether to return compact product attributes (default True) to optimize token usage"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_underlyings_of_product",
            "description": "Fetch underlying Bloomberg tickers for a structured product or RFQ. Returns a list of Underlying objects (underlyingBloombergTicker).",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Mandatory product identifier: Product ID (e.g. 'PRD-101', '101'), Valor ('126156101'), ISIN ('CH1261564201'), or RFQ ID ('RFQ-101')"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fees_of_product",
            "description": "Fetch fee schedule (name, amount, feeType, maturityType, isPricingRelevant) for a structured product. Returns a list of Fee objects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Mandatory product identifier: Product ID (e.g. 'PRD-101', '101'), Valor ('126156101'), ISIN ('CH1261564201'), or RFQ ID ('RFQ-101')"},
                    "fee_type": {"type": "string", "description": "Optional fee category filter (e.g. 'distribution', 'structuring', 'all')"},
                },
                "required": ["product_id"],
            },
        },
    },
]

GEMINI_PROMPT_CONTEXT = """You are the SLD Structured Products Assistant. You distribute and answer inquiries about structured products, their underlying Bloomberg tickers, and fee schedules in the SLD application.

You have access to 3 tools in your context:

1. get_rfqs(start_date=None, end_date=None, isin=None, valor=None, status=None, currency=None, issuer=None, product_type=None, underlying=None, limit=10, offset=0, compact=True)
   Description: Fetch structured products from SLD. Use date-based bounds, security identifiers, status/currency/issuer/underlying filters, and limit/offset to query subsets and protect context size. Returns bounded results with summary metadata.
   Parameters:
     - start_date: Start date of search period (e.g. '2026-09-28' or ISO format YYYY-MM-DD)
     - end_date: End date for search period (e.g. '2026-09-29' or ISO format YYYY-MM-DD)
     - isin: Security ISIN identifier (e.g. 'CH1261564201')
     - valor: Security Valor identifier (e.g. '126156101')
     - rfq_id: Specific product ID or RFQ ID (e.g. 'RFQ-101')
     - status: Product status ('open', 'quoted', 'traded', 'expired', 'rejected')
     - currency: Currency code (e.g. 'CHF', 'USD', 'EUR')
     - issuer: Quoting issuer bank (e.g. 'ZKB', 'UBS', 'Vontobel', 'BNP Paribas')
     - product_type: Structure type (e.g. 'Barrier Reverse Convertible', 'Autocallable')
     - underlying: Underlying ticker symbol (e.g. 'NESN', 'NOVN', 'AAPL')
     - limit: Max items to return (default 10, max 50)
     - offset: Pagination offset (default 0)
     - compact: Compact representation to keep context bounded (default True)

2. get_underlyings_of_product(product_id)
   Description: Fetch underlying Bloomberg tickers for a structured product. Returns a list of Underlying objects (underlyingBloombergTicker).
   Parameters:
     - product_id: Product ID (e.g. 'PRD-101', '101'), Valor (e.g. '126156101'), ISIN (e.g. 'CH1261564201'), or RFQ ID (e.g. 'RFQ-101') (REQUIRED)

3. get_fees_of_product(product_id, fee_type=None)
   Description: Fetch fee schedule for a product. Returns a list of Fee objects (name, amount, feeType, maturityType, isPricingRelevant).
   Parameters:
     - product_id: Product ID (e.g. 'PRD-101', '101'), Valor (e.g. '126156101'), ISIN (e.g. 'CH1261564201'), or RFQ ID (e.g. 'RFQ-101') (REQUIRED)
     - fee_type: Optional fee category ('distribution', 'structuring', 'all')

INSTRUCTIONS:
- Evaluate the user query. Determine which tools to call and with what parameters. You have date-based search capability via `start_date` and `end_date` on `get_rfqs`, as well as subset filters (`status`, `currency`, `issuer`, `product_type`, `underlying`) and `limit`.
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


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """JSON dump helper that converts Decimal, model_dump, and dataclasses safely."""
    def _default(o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        if hasattr(o, "model_dump"):
            return o.model_dump()
        if hasattr(o, "__dataclass_fields__"):
            return asdict(o)
        return str(o)
    if "default" not in kwargs:
        kwargs["default"] = _default
    return json.dumps(obj, **kwargs)


def _serialize_tool_output(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, list):
        return [_serialize_tool_output(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize_tool_output(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        d = asdict(obj)
        return _serialize_tool_output(d)
    return obj


def _compact_product(prod: Any) -> dict[str, Any]:
    gen = getattr(prod, "productGeneral", None) or prod
    pricing = getattr(prod, "productPricing", None)
    fees = getattr(prod, "productFees", None)

    und_list = getattr(gen, "underlyingList", None) or getattr(prod, "underlyings", []) or []
    tickers = [
        u.underlyingBloombergTicker if hasattr(u, "underlyingBloombergTicker")
        else (u.get("underlyingBloombergTicker") if isinstance(u, dict) else str(u))
        for u in und_list
    ]

    prod_id = getattr(gen, "productId", None) or getattr(prod, "product_id", None)
    rfq_id = getattr(prod, "rfq_id", None) or (f"RFQ-{prod_id}" if prod_id else None)
    isin = getattr(gen, "isin", None) or getattr(prod, "isin", None)
    valor = getattr(gen, "valor", None) or getattr(prod, "valor", None)
    name = getattr(gen, "productName", None) or getattr(prod, "product_name", None)
    currency = getattr(gen, "currency", None) or getattr(prod, "currency", None)
    nominal = getattr(gen, "productAmount", None) or getattr(prod, "nominal", None)
    ptype = getattr(gen, "productType", None) or getattr(prod, "product_type", None)
    status = getattr(prod, "status", None) or getattr(prod, "_status", "open")

    fair_val = None
    if pricing and hasattr(pricing, "fairValue") and pricing.fairValue is not None:
        fair_val = float(pricing.fairValue)
    elif isinstance(pricing, dict) and pricing.get("fairValue") is not None:
        fair_val = float(pricing["fairValue"])

    entry_costs = None
    if fees and hasattr(fees, "entryCosts") and fees.entryCosts is not None:
        entry_costs = float(fees.entryCosts)
    elif isinstance(fees, dict) and fees.get("entryCosts") is not None:
        entry_costs = float(fees["entryCosts"])

    return {
        "rfq_id": rfq_id,
        "product_id": f"PRD-{prod_id}" if prod_id and not str(prod_id).startswith("PRD-") else (str(prod_id) if prod_id else None),
        "productId": prod_id,
        "product_name": name,
        "productName": name,
        "isin": isin,
        "valor": valor,
        "currency": currency,
        "nominal": nominal,
        "productAmount": nominal,
        "product_type": ptype,
        "productType": ptype,
        "status": status,
        "_status": status,
        "fair_value": fair_val,
        "entry_costs": entry_costs,
        "underlyings": tickers,
        "productGeneral": {
            "productId": prod_id,
            "productName": name,
            "isin": isin,
            "valor": valor,
            "currency": currency,
            "productAmount": nominal,
            "productType": ptype,
            "underlyingList": [{"underlyingBloombergTicker": t} for t in tickers],
        },
        "productPricing": {"fairValue": fair_val} if fair_val is not None else {},
        "productFees": {"entryCosts": entry_costs} if entry_costs is not None else {},
    }


def _run_get_rfqs(args: dict[str, Any]) -> Any:
    start_date = args.get("start_date")
    end_date = args.get("end_date")
    isin = args.get("isin")
    valor = args.get("valor")
    rfq_id = args.get("rfq_id")
    status = args.get("status")
    currency = args.get("currency")
    issuer = args.get("issuer")
    product_type = args.get("product_type")
    underlying = args.get("underlying")
    client_name = args.get("client")
    compact = args.get("compact", True)

    limit = args.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 10
    else:
        # Default bounded limit for LLM context optimization unless querying by exact unique identifier
        if not isin and not valor and not (rfq_id and any(prefix in str(rfq_id).upper() for prefix in ["RFQ-", "PRD-", "CH"])):
            limit = 10

    offset = int(args.get("offset", 0)) if args.get("offset") is not None else 0

    if not isin and not valor and rfq_id:
        val = str(rfq_id).strip()
        if val.upper().startswith("CH") and len(val) == 12:
            isin = val
            rfq_id = None
        else:
            resolved = sld_service._resolve_key(val)
            if resolved and resolved in sld_service._products_by_id:
                isin = sld_service._products_by_id[resolved].isin
                valor = sld_service._products_by_id[resolved].valor
                rfq_id = None

    all_prods = sld_service.get_rfqs(
        start_date=start_date,
        end_date=end_date,
        isin=isin,
        valor=valor,
        currency=currency,
        status=status,
        issuer=issuer,
        product_type=product_type,
        underlying=underlying,
        rfq_id=rfq_id,
        client=client_name,
        limit=None,
        offset=0,
    )
    total_count = len(all_prods)

    paginated = all_prods[offset : offset + limit] if limit is not None else all_prods[offset:]

    if compact:
        serialized_items = [_compact_product(p) for p in paginated]
    else:
        serialized_items = _serialize_tool_output(paginated)

    return {
        "total_count": total_count,
        "returned_count": len(serialized_items),
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(serialized_items)) < total_count,
        "products": serialized_items,
        "items": serialized_items,
    }


TOOL_RUNNERS = {
    "get_rfqs": lambda args: _serialize_tool_output(_run_get_rfqs(args)),
    "get_underlyings_for_product": lambda args: _serialize_tool_output(sld_service.get_underlyings_for_product(product_id=args.get("product_id"))),
    "get_underlyings_of_product": lambda args: _serialize_tool_output(sld_service.get_underlyings_for_product(product_id=args.get("product_id"))),
    "get_fees_for_product": lambda args: _serialize_tool_output(sld_service.get_fees_for_product(product_id=args.get("product_id"))),
    "get_fees_of_product": lambda args: _serialize_tool_output(sld_service.get_fees_for_product(product_id=args.get("product_id"))),
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
        self.last_token_usage: TokenUsage | None = None

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    async def execute_and_interpret(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
        return_iterations: bool = False,
        return_usage: bool = False,
    ) -> Any:
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

        user_msg = message.strip()
        hist = list(history or [])
        if hist and hist[-1].role == "user" and hist[-1].content.strip() == user_msg:
            hist = hist[:-1]

        for item in hist:
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": user_msg})

        records: list[ToolCallRecord] = []
        iteration_steps: list[IterationStep] = []
        iteration = 0
        cumulative_tokens = 0
        last_step_usage: TokenUsage | None = None

        # Iterative loop: continue until LLM deems results sufficient or max_iterations reached
        while iteration < self.max_iterations:
            iteration += 1

            # Give tool descriptions and current context to the LLM
            tools_spec = None if is_prompt_only else SLD_TOOLS
            llm_decision = await self.llm_client.query(messages=messages, tools=tools_spec)

            step_usage = getattr(llm_decision, "token_usage", None)
            if not step_usage:
                step_usage = build_token_usage(
                    model_name=self.model_name,
                    messages=messages,
                    tools=tools_spec,
                    content=llm_decision.content,
                    tool_calls=llm_decision.tool_calls,
                )
            cumulative_tokens += step_usage.total_tokens
            last_step_usage = step_usage

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

                final_usage = TokenUsage(
                    prompt_tokens=step_usage.prompt_tokens,
                    completion_tokens=step_usage.completion_tokens,
                    total_tokens=step_usage.total_tokens,
                    context_window_limit=step_usage.context_window_limit,
                    context_window_used_pct=step_usage.context_window_used_pct,
                    cumulative_total_tokens=cumulative_tokens,
                )
                self.last_token_usage = final_usage

                if return_usage:
                    if return_iterations:
                        return final_content, records, iteration_steps, final_usage
                    return final_content, records, final_usage

                if return_iterations:
                    return final_content, records, iteration_steps
                return final_content, records

            # The LLM instructed the backend to call one or more tools
            current_step_tools: list[ToolCallRecord] = []
            thought_text = llm_decision.content or None

            if is_prompt_only:
                messages.append({
                    "role": "assistant",
                    "content": llm_decision.content or safe_json_dumps({"tool_calls": [tc.model_dump() for tc in llm_decision.tool_calls]}),
                })
                
                tool_results_texts: list[str] = []
                for tc in llm_decision.tool_calls:
                    runner = TOOL_RUNNERS.get(tc.name)
                    if not runner:
                        err_msg = f"Tool '{tc.name}' not found"
                        tool_results_texts.append(f"- Tool: {tc.name}\n  Error: Tool not found")
                        record = ToolCallRecord(
                            tool=tc.name,
                            parameters=_serialize_tool_output(tc.arguments),
                            summary=f"Tool '{tc.name}' not found",
                            error=err_msg,
                        )
                        records.append(record)
                        current_step_tools.append(record)
                        continue

                    try:
                        tool_output = _serialize_tool_output(runner(tc.arguments))
                        tool_results_texts.append(
                            f"- Tool: {tc.name}\n"
                            f"  Arguments: {safe_json_dumps(tc.arguments)}\n"
                            f"  Result: {safe_json_dumps(tool_output)}"
                        )
                        record = ToolCallRecord(
                            tool=tc.name,
                            parameters=_serialize_tool_output(tc.arguments),
                            summary=f"Executed {tc.name}",
                            result=tool_output,
                        )
                        records.append(record)
                        current_step_tools.append(record)
                    except Exception as exc:
                        tool_results_texts.append(
                            f"- Tool: {tc.name}\n"
                            f"  Arguments: {safe_json_dumps(tc.arguments)}\n"
                            f"  Error: {str(exc)}"
                        )
                        record = ToolCallRecord(
                            tool=tc.name,
                            parameters=_serialize_tool_output(tc.arguments),
                            summary=f"Failed: {exc}",
                            error=str(exc),
                        )
                        records.append(record)
                        current_step_tools.append(record)

                iteration_steps.append(
                    IterationStep(
                        iteration=iteration,
                        thought=thought_text,
                        tool_calls=current_step_tools,
                        token_usage=step_usage,
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
                # Role-based tool response for Native Tool Calling or Mock LLM client
                if getattr(llm_decision, "raw_message", None):
                    messages.append(llm_decision.raw_message)
                else:
                    messages.append({
                        "role": "assistant",
                        "content": llm_decision.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": safe_json_dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments),
                                },
                            }
                            for tc in llm_decision.tool_calls
                        ],
                    })

                # Backend executes the tool calls as instructed by the LLM
                for tc in llm_decision.tool_calls:
                    runner = TOOL_RUNNERS.get(tc.name)
                    if not runner:
                        err_msg = {"error": f"Tool '{tc.name}' not found"}
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": safe_json_dumps(err_msg),
                        })
                        record = ToolCallRecord(
                            tool=tc.name,
                            parameters=_serialize_tool_output(tc.arguments),
                            summary=f"Tool '{tc.name}' not found",
                            error=str(err_msg),
                        )
                        records.append(record)
                        current_step_tools.append(record)
                        continue

                    try:
                        tool_output = _serialize_tool_output(runner(tc.arguments))
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": safe_json_dumps(tool_output),
                        })
                        record = ToolCallRecord(
                            tool=tc.name,
                            parameters=_serialize_tool_output(tc.arguments),
                            summary=f"Executed {tc.name}",
                            result=tool_output,
                        )
                        records.append(record)
                        current_step_tools.append(record)
                    except Exception as exc:
                        err_output = {"error": str(exc)}
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": safe_json_dumps(err_output),
                        })
                        record = ToolCallRecord(
                            tool=tc.name,
                            parameters=_serialize_tool_output(tc.arguments),
                            summary=f"Failed: {exc}",
                            error=str(exc),
                        )
                        records.append(record)
                        current_step_tools.append(record)

                iteration_steps.append(
                    IterationStep(
                        iteration=iteration,
                        thought=thought_text,
                        tool_calls=current_step_tools,
                        token_usage=step_usage,
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

        fallback_usage = getattr(fallback_response, "token_usage", None)
        if not fallback_usage:
            fallback_usage = build_token_usage(
                model_name=self.model_name,
                messages=messages,
                tools=None,
                content=fallback_response.content,
            )
        cumulative_tokens += fallback_usage.total_tokens
        final_usage = TokenUsage(
            prompt_tokens=fallback_usage.prompt_tokens,
            completion_tokens=fallback_usage.completion_tokens,
            total_tokens=fallback_usage.total_tokens,
            context_window_limit=fallback_usage.context_window_limit,
            context_window_used_pct=fallback_usage.context_window_used_pct,
            cumulative_total_tokens=cumulative_tokens,
        )
        self.last_token_usage = final_usage

        fallback_text = fallback_response.content or "Completed with maximum iterations reached."
        if return_usage:
            if return_iterations:
                return fallback_text, records, iteration_steps, final_usage
            return fallback_text, records, final_usage

        if return_iterations:
            return fallback_text, records, iteration_steps
        return fallback_text, records

    async def generate_reply(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> str:
        res = await self.execute_and_interpret(message=message, history=history)
        return res[0]


dummy_llm_service = LLMService(llm_client=mock_llm_client)
gemini_llm_service = LLMService(llm_client=gemini_llm_client)
gemini_native_llm_service = LLMService(llm_client=gemini_native_llm_client)


def get_llm_service(mode: str | None = None) -> LLMService:
    """Retrieve LLM service for the requested mode ('mock', 'gemini-native', or 'gemini')."""
    selected = (mode or os.getenv("LLM_MODE", "mock")).lower().strip()
    if selected in ("gemini-native", "native", "gemini-tools", "gemini-function-calling"):
        return gemini_native_llm_service
    if selected in ("gemini", "gemini-3.8-flash", "live", "gemini-prompt"):
        return gemini_llm_service
    return dummy_llm_service
