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
    """Mock of a proper LLM client with query() interface and tool-calling support.
    
    Swap this implementation with a real LLM endpoint (e.g. OpenAI, Anthropic, or an internal LLM)
    by updating query() to invoke your real model.
    """

    model_name = "mock-sld-llm-v1"

    async def query(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Query the LLM with messages and optional tool specifications.
        
        - If tools are provided and the user query requires data, returns tool_calls.
        - If tool results are present in messages (role='tool'), interprets them into a final response.
        - Otherwise returns a conversational content reply.
        """
        # 1. Check if we have tool outputs to interpret
        tool_results = [m for m in messages if m.get("role") == "tool"]
        if tool_results:
            return self._interpret_tool_results(tool_results)

        # 2. Extract the latest user query and previous context
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

        # Handle greetings and generic help without calling tools
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

        # If tools are available, simulate LLM tool selection and parameter extraction
        if tools:
            tool_calls = self._simulate_llm_tool_selection(user_message, history_texts, tools)
            if tool_calls:
                return LLMResponse(content=None, tool_calls=tool_calls)

        # Default conversational reply if no tools matched
        return LLMResponse(
            content=(
                f"I received your inquiry: {user_message!r}. "
                "You can ask me about SLD RFQs (`get_rfqs`), product underlyings (`get_underlyings_of_product`), "
                "or fee schedules (`get_fees_of_product`)."
            )
        )

    def _simulate_llm_tool_selection(
        self,
        user_message: str,
        history: list[str],
        tools: list[dict[str, Any]],
    ) -> list[LLMToolCall]:
        """Simulate how an LLM parses semantic intent and tool parameters."""
        tool_names = {t["function"]["name"] for t in tools if "function" in t}
        lower = user_message.lower()

        # Extract identifiers from user query or recent history
        rfq_match = re.search(r"\b(RFQ[-_ ]?\d+)\b", user_message, re.IGNORECASE)
        rfq_id = None
        if rfq_match:
            rfq_id = re.sub(r"[-_ ]", "-", rfq_match.group(1)).upper()
            if not rfq_id.startswith("RFQ-"):
                rfq_id = "RFQ-" + rfq_id[3:]

        isin_match = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}\d)\b", user_message, re.IGNORECASE)
        isin = isin_match.group(1).upper() if isin_match else None

        prd_match = re.search(r"\b(PRD[-_ ]?\d+)\b", user_message, re.IGNORECASE)
        product_id = None
        if prd_match:
            product_id = re.sub(r"[-_ ]", "-", prd_match.group(1)).upper()
            if not product_id.startswith("PRD-"):
                product_id = "PRD-" + product_id[3:]
        elif isin:
            product_id = isin
        elif rfq_id:
            product_id = rfq_id

        # Carryover from history
        if not product_id and not rfq_id:
            for text in reversed(history[-6:]):
                hist_rfq = re.search(r"\b(RFQ[-_ ]?\d+)\b", text, re.IGNORECASE)
                if hist_rfq:
                    rfq_id = re.sub(r"[-_ ]", "-", hist_rfq.group(1)).upper()
                    if not rfq_id.startswith("RFQ-"):
                        rfq_id = "RFQ-" + rfq_id[3:]
                    product_id = rfq_id
                    break
                hist_isin = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}\d)\b", text, re.IGNORECASE)
                if hist_isin:
                    isin = hist_isin.group(1).upper()
                    product_id = isin
                    break

        # Check intent
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

        selected_calls: list[LLMToolCall] = []

        if is_asking_underlyings and "get_underlyings_of_product" in tool_names:
            selected_calls.append(
                LLMToolCall(
                    id=f"call_{len(selected_calls)+1}",
                    name="get_underlyings_of_product",
                    arguments={"product_id": product_id or "RFQ-101"},
                )
            )

        if is_asking_fees and "get_fees_of_product" in tool_names:
            fee_type = "distribution" if "distribution" in lower else ("structuring" if "structuring" in lower else None)
            args: dict[str, Any] = {"product_id": product_id or "RFQ-101"}
            if fee_type:
                args["fee_type"] = fee_type
            selected_calls.append(
                LLMToolCall(
                    id=f"call_{len(selected_calls)+1}",
                    name="get_fees_of_product",
                    arguments=args,
                )
            )

        if (has_rfq_intent or not selected_calls) and "get_rfqs" in tool_names:
            rfq_args: dict[str, Any] = {}
            if rfq_id:
                rfq_args["rfq_id"] = rfq_id
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
            selected_calls.append(
                LLMToolCall(
                    id=f"call_{len(selected_calls)+1}",
                    name="get_rfqs",
                    arguments=rfq_args,
                )
            )

        return selected_calls

    def _interpret_tool_results(self, tool_results: list[dict[str, Any]]) -> LLMResponse:
        """Simulate LLM interpretation of tool output JSON."""
        sections: list[str] = []

        for tr in tool_results:
            name = tr.get("name")
            content_raw = tr.get("content")
            data = json.loads(content_raw) if isinstance(content_raw, str) else content_raw

            if name == "get_underlyings_of_product":
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

            elif name == "get_fees_of_product":
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

            elif name == "get_rfqs":
                rfqs = data if isinstance(data, list) else []
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

        return LLMResponse(content="\n\n---\n\n".join(sections))


mock_llm_client = MockLLMClient()
