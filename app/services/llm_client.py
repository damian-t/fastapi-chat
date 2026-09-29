import json
import re
from typing import Any
from pydantic import BaseModel, Field


class LLMToolCall(BaseModel):
    id: str = Field(default="call_mock_1")
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)

    def __str__(self) -> str:
        return self.content or ""


class MockLLMClient:
    """Mock of an intelligent LLM that supports multi-turn tool calling and iterative reasoning.
    
    1. Evaluates user query and available tools.
    2. Determines which calls to make in order with appropriate arguments.
    3. Evaluates if the tool results returned by the backend are sufficient.
    4. If sufficient, returns the final interpretation.
    5. If not sufficient, returns additional tool calls.
    """

    model_name = "mock-sld-llm-v2"

    async def query(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        user_message = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_message = str(m.get("content", ""))
                break

        history_texts = [
            str(m.get("content", "")) for m in messages if m.get("role") in {"user", "assistant"}
        ]

        lower = user_message.lower().strip()
        cleaned_alpha = re.sub(r"[^a-zA-Z\s]", "", lower).strip()

        # Handle greetings and generic help immediately without tool calls
        if cleaned_alpha in {"hi", "hello", "hey", "hallo", "hoi", "good morning", "good day", "greetings"}:
            return LLMResponse(
                content=(
                    "👋 **Hello! I am your SLD Structured Products Assistant.**\n\n"
                    "I connect directly to the **SLD application** to manage and query Requests for Quotes (RFQs), "
                    "underlying basket performance, and fee schedules for structured products.\n\n"
                    "Here are some questions you can ask me:\n"
                    "• *'Show all open RFQs in USD'*\n"
                    "• *'What quotes do we have for RFQ-101?'*\n"
                    "• *'What are the underlyings of RFQ-102?'*\n"
                    "• *'What is the fee breakdown for product CH1261564201?'*\n"
                    "• *'Check the underlyings and fees for RFQ-104'*"
                )
            )

        if "help" in lower or "what can you do" in lower or "available tools" in lower:
            return LLMResponse(
                content=(
                    "💡 **SLD Chatbot Capabilities & Integrated Tools:**\n\n"
                    "I determine your intent and query the following SLD REST tools:\n\n"
                    "1. `get_rfqs(rfq_id, status, issuer, product_type, currency, limit)`\n"
                    "   Queries structured product RFQs by lifecycle state, issuer quotes, or product category.\n"
                    "2. `get_underlyings_of_product(product_id)`\n"
                    "   Fetches basket constituents, spot vs current prices, barrier levels, and breach checks.\n"
                    "3. `get_fees_of_product(product_id, fee_type)`\n"
                    "   Extracts distribution fees, structuring fees, recurring management fees, and monetary totals.\n\n"
                    "Try: *'Show me quoted RFQs'* or *'What underlyings are in RFQ-101?'*"
                )
            )

        # Collect executed tool results already provided by the backend
        executed_tools: dict[str, Any] = {}
        for m in messages:
            if m.get("role") == "tool":
                name = m.get("name")
                raw = m.get("content", "")
                try:
                    executed_tools[name] = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    executed_tools[name] = raw

        # Identify required information
        needed_tools = self._detect_needed_tools(user_message, history_texts)

        # Check if the tools returned so far are sufficient to answer the user query
        is_sufficient = bool(
            executed_tools
            and all(t in executed_tools for t in needed_tools)
        )

        # If sufficient or no tools are being provided, interpret the results
        if is_sufficient or not tools:
            return self._interpret_tool_results(executed_tools, user_message)

        # Otherwise, the LLM determines what additional calls are still needed
        remaining_tools = [t for t in needed_tools if t not in executed_tools]
        if not remaining_tools and not executed_tools:
            remaining_tools = ["get_rfqs"]

        next_calls = self._plan_tool_calls(
            remaining_tools, user_message, history_texts, executed_tools, tools
        )

        if next_calls:
            return LLMResponse(content=None, tool_calls=next_calls)

        # Fallback interpretation if no more tool calls can be planned
        return self._interpret_tool_results(executed_tools, user_message)

    def _detect_needed_tools(self, user_message: str, history: list[str]) -> list[str]:
        """Detect what tools are required to answer the user inquiry."""
        lower = user_message.lower()
        needed = []

        is_asking_underlyings = bool(
            re.search(r"\b(underlying|underlyings|basket|shares|stocks|components|barrier|strike|spot)\b", lower)
        )
        is_asking_fees = bool(
            re.search(r"\b(fee|fees|cost|costs|pricing|margin|ter|structuring fee|distribution fee)\b", lower)
        )

        text_without_rfq_ids = re.sub(r"\bRFQ[-_ ]?\d+\b", "", lower, flags=re.IGNORECASE)
        has_rfq_intent = bool(
            re.search(
                r"\b(rfq|rfqs|quote|quotes|request for quote|requests for quotes|trades|orders|pipeline|lifecycle)\b",
                text_without_rfq_ids,
            )
            or any(s in lower for s in ["open", "quoted", "traded", "expired", "rejected"])
            or any(c in user_message.upper() for c in ["CHF", "USD", "EUR"])
            or (any(iss in lower for iss in ["zkb", "ubs", "vontobel", "bnp", "lukb"]) and not is_asking_underlyings and not is_asking_fees)
        )

        # Check multi-step dependency: e.g. "What are the fees for the open Swiss RFQ?"
        # Needs get_rfqs first to find the product ID, then get_fees_of_product!
        rfq_match = re.search(r"\b(RFQ[-_ ]?\d+)\b", user_message, re.IGNORECASE)
        has_direct_id = bool(rfq_match or re.search(r"\b([A-Z]{2}[A-Z0-9]{9}\d)\b", user_message, re.IGNORECASE) or re.search(r"\b(PRD[-_ ]?\d+)\b", user_message, re.IGNORECASE))

        if not has_direct_id and (is_asking_fees or is_asking_underlyings) and any(kw in lower for kw in ["open", "traded", "quoted", "swiss", "usd", "chf"]):
            # Multi-step: must find the RFQ first
            needed.append("get_rfqs")

        if is_asking_underlyings:
            needed.append("get_underlyings_of_product")
        if is_asking_fees:
            needed.append("get_fees_of_product")
        if has_rfq_intent and "get_rfqs" not in needed:
            needed.append("get_rfqs")

        if not needed:
            needed.append("get_rfqs")

        return needed

    def _plan_tool_calls(
        self,
        remaining_tools: list[str],
        user_message: str,
        history: list[str],
        executed_tools: dict[str, Any],
        tools: list[dict[str, Any]],
    ) -> list[LLMToolCall]:
        """Determine specific tool calls with arguments, resolving dependencies from prior results."""
        available_tool_names = {t["function"]["name"] for t in tools if "function" in t}
        lower = user_message.lower()

        # Resolve product_id from direct input, history, or prior executed tool outputs
        product_id = None

        # 1. From executed RFQ tool results (multi-step dependency!)
        if "get_rfqs" in executed_tools:
            rfq_data = executed_tools["get_rfqs"]
            if isinstance(rfq_data, list) and len(rfq_data) > 0:
                first_rfq = rfq_data[0]
                product_id = first_rfq.get("product_id") or first_rfq.get("rfq_id")

        # 2. From direct message
        if not product_id:
            rfq_match = re.search(r"\b(RFQ[-_ ]?\d+)\b", user_message, re.IGNORECASE)
            if rfq_match:
                product_id = re.sub(r"[-_ ]", "-", rfq_match.group(1)).upper()
                if not product_id.startswith("RFQ-"):
                    product_id = "RFQ-" + product_id[3:]

        if not product_id:
            isin_match = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}\d)\b", user_message, re.IGNORECASE)
            if isin_match:
                product_id = isin_match.group(1).upper()

        if not product_id:
            prd_match = re.search(r"\b(PRD[-_ ]?\d+)\b", user_message, re.IGNORECASE)
            if prd_match:
                product_id = re.sub(r"[-_ ]", "-", prd_match.group(1)).upper()
                if not product_id.startswith("PRD-"):
                    product_id = "PRD-" + product_id[3:]

        # 3. From history carryover
        if not product_id:
            for text in reversed(history[-6:]):
                hist_rfq = re.search(r"\b(RFQ[-_ ]?\d+)\b", text, re.IGNORECASE)
                if hist_rfq:
                    product_id = re.sub(r"[-_ ]", "-", hist_rfq.group(1)).upper()
                    if not product_id.startswith("RFQ-"):
                        product_id = "RFQ-" + product_id[3:]
                    break
                hist_isin = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}\d)\b", text, re.IGNORECASE)
                if hist_isin:
                    product_id = hist_isin.group(1).upper()
                    break

        planned: list[LLMToolCall] = []

        # If get_rfqs is required and not yet executed, execute it first
        if "get_rfqs" in remaining_tools and "get_rfqs" in available_tool_names:
            rfq_args: dict[str, Any] = {}
            if product_id and product_id.startswith("RFQ-"):
                rfq_args["rfq_id"] = product_id
            for status in ["open", "quoted", "traded", "expired", "rejected"]:
                if status in lower:
                    rfq_args["status"] = status
                    break
            for curr in ["CHF", "USD", "EUR"]:
                if curr in user_message.upper():
                    rfq_args["currency"] = curr
                    break
            for iss in ["ZKB", "UBS", "Vontobel", "BNP Paribas"]:
                if iss.lower() in lower:
                    rfq_args["issuer"] = iss
                    break
            planned.append(
                LLMToolCall(
                    id=f"call_{len(planned)+1}",
                    name="get_rfqs",
                    arguments=rfq_args,
                )
            )
            # If get_rfqs is discovering an unknown product, execute get_rfqs first
            # so the next iteration can use its output to call product fees/underlyings
            if not product_id and (len(remaining_tools) > 1):
                return planned

        # Plan underlyings
        if "get_underlyings_of_product" in remaining_tools and "get_underlyings_of_product" in available_tool_names:
            planned.append(
                LLMToolCall(
                    id=f"call_{len(planned)+1}",
                    name="get_underlyings_of_product",
                    arguments={"product_id": product_id or "RFQ-101"},
                )
            )

        # Plan fees
        if "get_fees_of_product" in remaining_tools and "get_fees_of_product" in available_tool_names:
            fee_type = "distribution" if "distribution" in lower else ("structuring" if "structuring" in lower else None)
            args: dict[str, Any] = {"product_id": product_id or "RFQ-101"}
            if fee_type:
                args["fee_type"] = fee_type
            planned.append(
                LLMToolCall(
                    id=f"call_{len(planned)+1}",
                    name="get_fees_of_product",
                    arguments=args,
                )
            )

        return planned

    def _interpret_tool_results(
        self, executed_tools: dict[str, Any], user_message: str
    ) -> LLMResponse:
        """Interpret all gathered tool outputs and synthesize a comprehensive answer."""
        if not executed_tools:
            return LLMResponse(
                content=(
                    f"I received your inquiry: {user_message!r}. "
                    "You can ask me about SLD RFQs (`get_rfqs`), product underlyings (`get_underlyings_of_product`), "
                    "or fee schedules (`get_fees_of_product`)."
                )
            )

        sections: list[str] = []

        # 1. Underlyings
        if "get_underlyings_of_product" in executed_tools:
            data = executed_tools["get_underlyings_of_product"]
            if isinstance(data, dict) and "underlyings" in data:
                lines = [
                    f"📊 **Underlying Assets for {data['product_name']}** (`{data['isin']}` / `{data['product_id']}`)",
                    f"• **Basket Structure:** {data['basket_type']}",
                    "",
                ]
                for u in data.get("underlyings", []):
                    perf = u.get("performance_pct", 0.0)
                    perf_sym = "🟢" if perf >= 0 else "🔴"
                    barrier_pct = u.get("barrier_level_pct")
                    dist = u.get("distance_to_barrier_pct")
                    barrier_str = (
                        f"{barrier_pct}% (Distance: +{dist:.2f}%)"
                        if barrier_pct is not None
                        else "No Barrier (Capital Protected)"
                    )
                    hit_str = "⚠️ **BREACHED**" if u.get("barrier_hit") else "✅ Safe (Intact)"
                    lines.append(
                        f"• **{u['name']}** (`{u['ticker']}` - {u['currency']}):\n"
                        f"  - Spot / Current: {u['spot_price']:.2f} → {u['current_price']:.2f} ({perf_sym} {perf:+.2f}%)\n"
                        f"  - Strike: {u['strike_level_pct']}%\n"
                        f"  - Barrier: {barrier_str} [{hit_str}]"
                    )
                sections.append("\n".join(lines))
            elif isinstance(data, dict) and "error" in data:
                sections.append(f"❌ **Error querying underlyings:** {data['error']}")

        # 2. Fees
        if "get_fees_of_product" in executed_tools:
            data = executed_tools["get_fees_of_product"]
            if isinstance(data, dict) and "total_fee_pct" in data:
                lines = [
                    f"💰 **Fee Structure for {data['product_name']}** (`{data['isin']}`)",
                    f"• **Base Nominal:** {data['currency']} {data['nominal']:,.2f}",
                    f"• **Distribution Fee:** {data['distribution_fee_pct']:.2f}% ({data['distribution_fee_pct'] * 100:.0f} bps)",
                    f"• **Structuring Fee:** {data['structuring_fee_pct']:.2f}% ({data['structuring_fee_pct'] * 100:.0f} bps)",
                    f"• **Management Fee (p.a.):** {data['management_fee_pct_pa']:.2f}%",
                    f"• **Exchange / Settlement Fee:** {data['exchange_fee_pct']:.2f}%",
                    f"• **Total Expense / Fee:** **{data['total_fee_pct']:.2f}%**",
                    f"• **Estimated Cost on Nominal:** **{data['currency']} {data['estimated_monetary_amount']:,.2f}**",
                    f"• *Note:* {data['description']}",
                ]
                sections.append("\n".join(lines))
            elif isinstance(data, dict) and "error" in data:
                sections.append(f"❌ **Error querying fees:** {data['error']}")

        # 3. RFQs
        if "get_rfqs" in executed_tools:
            rfqs = executed_tools["get_rfqs"]
            if isinstance(rfqs, list):
                if not rfqs:
                    sections.append("🔍 No RFQs found matching the requested criteria.")
                else:
                    lines = [f"📋 **SLD RFQ Results** ({len(rfqs)} found):", ""]
                    for r in rfqs:
                        status_badge = {
                            "open": "🟡 OPEN",
                            "quoted": "🔵 QUOTED",
                            "traded": "🟢 TRADED",
                            "expired": "⚪ EXPIRED",
                            "rejected": "🔴 REJECTED",
                        }.get(r.get("status"), str(r.get("status")).upper())

                        lines.append(f"**{r['rfq_id']}** — {r['product_name']} [{status_badge}]")
                        lines.append(f"  • **ISIN / ID:** `{r['isin']}` | `{r['product_id']}`")
                        lines.append(
                            f"  • **Type:** {r['product_type']} | **Volume:** {r['currency']} {r['nominal']:,.0f} | **Client:** {r['client']}"
                        )
                        lines.append(f"  • **Underlyings:** {', '.join(r.get('underlyings', []))}")

                        if r.get("status") == "traded":
                            lines.append(
                                f"  • **Execution:** Traded with **{r.get('traded_with')}** at {r.get('traded_price_pct', 0):.2f}%"
                            )
                        elif r.get("best_quote"):
                            bq = r["best_quote"]
                            lines.append(
                                f"  • **Best Quote:** **{bq['issuer']}** @ {bq['price_pct']:.2f}% "
                                f"(Coupon: {bq['coupon_pct_pa']:.2f}% p.a.)"
                            )
                            quotes = r.get("quotes", [])
                            if len(quotes) > 1:
                                other_issuers = [q["issuer"] for q in quotes if q["issuer"] != bq["issuer"]]
                                lines.append(f"  • **Other Quotes:** {', '.join(other_issuers)} ({len(quotes)} total)")
                        elif r.get("status") == "open":
                            lines.append("  • **Quotes:** Awaiting pricing from market makers")

                        lines.append("")
                    sections.append("\n".join(lines).strip())
            elif isinstance(rfqs, dict) and "error" in rfqs:
                sections.append(f"❌ **Error querying RFQs:** {rfqs['error']}")

        return LLMResponse(content="\n\n---\n\n".join(sections))


mock_llm_client = MockLLMClient()
