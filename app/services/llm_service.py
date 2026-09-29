import re
from typing import Any
from app.models.chat import ChatMessage, ToolCallRecord
from app.services.sld_service import sld_service


class DummyLLMService:
    """Mock LLM Service that simulates intent understanding, tool determination,
    execution of SLD APIs, and financial result interpretation.
    """

    model_name = "sld-assistant-dummy-v1"

    def _extract_identifiers(self, text: str, history: list[ChatMessage] | None = None) -> dict[str, str | None]:
        """Extract RFQ ID, ISIN, or Product ID from current message or recent history."""
        # 1. Match RFQ IDs like RFQ-101, RFQ101, rfq-102
        rfq_match = re.search(r"\b(RFQ[-_ ]?\d+)\b", text, re.IGNORECASE)
        rfq_id = None
        if rfq_match:
            rfq_id = re.sub(r"[-_ ]", "-", rfq_match.group(1)).upper()
            if not rfq_id.startswith("RFQ-"):
                rfq_id = "RFQ-" + rfq_id[3:]

        # 2. Match ISIN (e.g. CH1261564201)
        isin_match = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}\d)\b", text, re.IGNORECASE)
        isin = isin_match.group(1).upper() if isin_match else None

        # 3. Match Product ID like PRD-101, PRD101
        prd_match = re.search(r"\b(PRD[-_ ]?\d+)\b", text, re.IGNORECASE)
        product_id = None
        if prd_match:
            product_id = re.sub(r"[-_ ]", "-", prd_match.group(1)).upper()
            if not product_id.startswith("PRD-"):
                product_id = "PRD-" + product_id[3:]
        elif isin:
            product_id = isin
        elif rfq_id:
            product_id = rfq_id

        # If not found in text, look back in history for context resolution
        if not product_id and not rfq_id and history:
            for past in reversed(history[-6:]):
                hist_rfq = re.search(r"\b(RFQ[-_ ]?\d+)\b", past.content, re.IGNORECASE)
                if hist_rfq:
                    rfq_id = re.sub(r"[-_ ]", "-", hist_rfq.group(1)).upper()
                    if not rfq_id.startswith("RFQ-"):
                        rfq_id = "RFQ-" + rfq_id[3:]
                    product_id = rfq_id
                    break
                hist_isin = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}\d)\b", past.content, re.IGNORECASE)
                if hist_isin:
                    isin = hist_isin.group(1).upper()
                    product_id = isin
                    break

        return {"rfq_id": rfq_id, "product_id": product_id, "isin": isin}

    def _extract_rfq_filters(self, text: str) -> dict[str, Any]:
        """Extract status, currency, issuer, and product type filters."""
        filters: dict[str, Any] = {}
        lower = text.lower()

        # Status
        for status in ["open", "quoted", "traded", "expired", "rejected"]:
            if re.search(rf"\b{status}\b", lower):
                filters["status"] = status
                break
        if "pending" in lower and "status" not in filters:
            filters["status"] = "open"

        # Currency
        for curr in ["CHF", "USD", "EUR", "GBP", "JPY"]:
            if re.search(rf"\b{curr}\b", text, re.IGNORECASE):
                filters["currency"] = curr.upper()
                break

        # Issuers
        for iss in ["ZKB", "UBS", "Vontobel", "BNP Paribas", "BNP", "LUKB"]:
            if iss.lower() in lower:
                filters["issuer"] = "BNP Paribas" if iss.lower() == "bnp" else iss
                break

        # Product Type
        if "autocallable" in lower:
            filters["product_type"] = "Autocallable"
        elif "brc" in lower or "barrier reverse" in lower:
            filters["product_type"] = "Barrier Reverse"
        elif "capital protection" in lower:
            filters["product_type"] = "Capital Protection"
        elif "reverse convertible" in lower:
            filters["product_type"] = "Reverse Convertible"

        return filters

    def _determine_tools(
        self,
        message: str,
        ids: dict[str, str | None],
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Determine which SLD tools to call and with what parameters."""
        lower = message.lower()
        tools_to_call: list[dict[str, Any]] = []

        is_asking_underlyings = bool(
            re.search(r"\b(underlying|underlyings|basket|shares|stocks|components|barrier|strike|spot)\b", lower)
        )
        is_asking_fees = bool(
            re.search(r"\b(fee|fees|cost|costs|pricing|margin|ter|structuring fee|distribution fee)\b", lower)
        )

        # Check explicit RFQ keywords without counting the RFQ-xxx ID itself
        text_without_rfq_ids = re.sub(r"\bRFQ[-_ ]?\d+\b", "", lower, flags=re.IGNORECASE)
        has_explicit_rfq_intent = bool(
            re.search(
                r"\b(rfq|rfqs|quote|quotes|request for quote|requests for quotes|trades|orders|pipeline|lifecycle)\b",
                text_without_rfq_ids,
            )
            or filters.get("status")
            or filters.get("currency")
            or (filters.get("issuer") and not is_asking_underlyings and not is_asking_fees)
        )

        target_product = ids.get("product_id") or ids.get("rfq_id")

        # 1. Underlyings Tool
        if is_asking_underlyings:
            tools_to_call.append({
                "tool": "get_underlyings_of_product",
                "parameters": {"product_id": target_product},
            })

        # 2. Fees Tool
        if is_asking_fees:
            fee_type = None
            if "distribution" in lower:
                fee_type = "distribution"
            elif "structuring" in lower:
                fee_type = "structuring"
            tools_to_call.append({
                "tool": "get_fees_of_product",
                "parameters": {"product_id": target_product, "fee_type": fee_type},
            })

        # 3. RFQs Tool
        # Call get_rfqs if explicit RFQ intent exists, or if no other tools were matched yet
        if has_explicit_rfq_intent or not tools_to_call:
            rfq_params: dict[str, Any] = {}
            if ids.get("rfq_id"):
                rfq_params["rfq_id"] = ids["rfq_id"]
            if filters.get("status"):
                rfq_params["status"] = filters["status"]
            if filters.get("currency"):
                rfq_params["currency"] = filters["currency"]
            if filters.get("issuer"):
                rfq_params["issuer"] = filters["issuer"]
            if filters.get("product_type"):
                rfq_params["product_type"] = filters["product_type"]

            tools_to_call.append({
                "tool": "get_rfqs",
                "parameters": rfq_params,
            })

        return tools_to_call

    async def execute_and_interpret(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> tuple[str, list[ToolCallRecord]]:
        """Understand question, plan tool calls, execute them, and interpret financial results."""
        clean_text = message.strip()
        lower = clean_text.lower()
        cleaned_alpha = re.sub(r"[^a-zA-Z\s]", "", lower).strip()

        # Handle greetings & general queries
        if cleaned_alpha in {"hi", "hello", "hey", "hallo", "hoi", "good morning", "good day", "greetings"}:
            greeting = (
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
            return greeting, []

        if "help" in lower or "what can you do" in lower or "available tools" in lower:
            help_text = (
                "💡 **SLD Chatbot Capabilities & Integrated Tools:**\n\n"
                "I determine your intent and automatically query the following SLD mock REST tools:\n\n"
                "1. `get_rfqs(rfq_id, status, issuer, product_type, currency, limit)`\n"
                "   Queries structured product RFQs by lifecycle state, issuer quotes, or product category.\n"
                "2. `get_underlyings_of_product(product_id)`\n"
                "   Fetches basket constituents, spot vs current prices, barrier levels, and breach checks.\n"
                "3. `get_fees_of_product(product_id, fee_type)`\n"
                "   Extracts distribution fees, structuring fees, recurring management fees, and monetary totals.\n\n"
                "Try: *'Show me quoted RFQs'* or *'What underlyings are in RFQ-101?'*"
            )
            return help_text, []

        ids = self._extract_identifiers(clean_text, history)
        filters = self._extract_rfq_filters(clean_text)
        planned_tools = self._determine_tools(clean_text, ids, filters)

        records: list[ToolCallRecord] = []
        sections: list[str] = []

        # Execute planned tools
        for plan in planned_tools:
            tool_name = plan["tool"]
            params = plan["parameters"]

            if tool_name == "get_underlyings_of_product":
                prod_id = params.get("product_id")
                if not prod_id:
                    sections.append(
                        "⚠️ **Missing Parameter:** To fetch product underlyings, please specify a Product ID, "
                        "ISIN, or RFQ ID (e.g., `RFQ-101`, `RFQ-102`, `CH1261564201`)."
                    )
                    continue

                try:
                    res = sld_service.get_underlyings_of_product(prod_id)
                    records.append(
                        ToolCallRecord(
                            tool="get_underlyings_of_product",
                            parameters={"product_id": prod_id},
                            summary=f"Found {len(res.underlyings)} underlyings for {res.product_name}",
                        )
                    )

                    lines = [
                        f"📊 **Underlying Assets for {res.product_name}** (`{res.isin}` / `{res.product_id}`)",
                        f"• **Basket Structure:** {res.basket_type}",
                        "",
                    ]
                    for u in res.underlyings:
                        perf_symbol = "🟢" if u.performance_pct >= 0 else "🔴"
                        barrier_str = (
                            f"{u.barrier_level_pct}% (Distance: +{u.distance_to_barrier_pct:.2f}%)"
                            if u.barrier_level_pct is not None
                            else "No Barrier (Capital Protected)"
                        )
                        hit_str = "⚠️ **BREACHED**" if u.barrier_hit else "✅ Safe (Intact)"
                        lines.append(
                            f"• **{u.name}** (`{u.ticker}` - {u.currency}):\n"
                            f"  - Spot / Current: {u.spot_price:.2f} → {u.current_price:.2f} ({perf_symbol} {u.performance_pct:+.2f}%)\n"
                            f"  - Strike: {u.strike_level_pct}%\n"
                            f"  - Barrier: {barrier_str} [{hit_str}]"
                        )
                    sections.append("\n".join(lines))
                except ValueError as err:
                    sections.append(f"❌ **Error querying underlyings:** {err}")

            elif tool_name == "get_fees_of_product":
                prod_id = params.get("product_id")
                fee_type = params.get("fee_type")
                if not prod_id:
                    sections.append(
                        "⚠️ **Missing Parameter:** To fetch product fees, please specify a Product ID, "
                        "ISIN, or RFQ ID (e.g., `RFQ-101`, `RFQ-103`, `CH1261564201`)."
                    )
                    continue

                try:
                    fees = sld_service.get_fees_of_product(prod_id, fee_type=fee_type)
                    records.append(
                        ToolCallRecord(
                            tool="get_fees_of_product",
                            parameters={"product_id": prod_id, "fee_type": fee_type},
                            summary=f"Total fee {fees.total_fee_pct}% ({fees.currency} {fees.estimated_monetary_amount:,.2f})",
                        )
                    )

                    lines = [
                        f"💰 **Fee Structure for {fees.product_name}** (`{fees.isin}`)",
                        f"• **Base Nominal:** {fees.currency} {fees.nominal:,.2f}",
                        f"• **Distribution Fee:** {fees.distribution_fee_pct:.2f}% ({fees.distribution_fee_pct * 100:.0f} bps)",
                        f"• **Structuring Fee:** {fees.structuring_fee_pct:.2f}% ({fees.structuring_fee_pct * 100:.0f} bps)",
                        f"• **Management Fee (p.a.):** {fees.management_fee_pct_pa:.2f}%",
                        f"• **Exchange / Settlement Fee:** {fees.exchange_fee_pct:.2f}%",
                        f"• **Total Expense / Fee:** **{fees.total_fee_pct:.2f}%**",
                        f"• **Estimated Cost on Nominal:** **{fees.currency} {fees.estimated_monetary_amount:,.2f}**",
                        f"• *Note:* {fees.description}",
                    ]
                    sections.append("\n".join(lines))
                except ValueError as err:
                    sections.append(f"❌ **Error querying fees:** {err}")

            elif tool_name == "get_rfqs":
                rfqs = sld_service.get_rfqs(
                    rfq_id=params.get("rfq_id"),
                    status=params.get("status"),
                    issuer=params.get("issuer"),
                    product_type=params.get("product_type"),
                    currency=params.get("currency"),
                    limit=10,
                )
                records.append(
                    ToolCallRecord(
                        tool="get_rfqs",
                        parameters=params,
                        summary=f"Retrieved {len(rfqs)} RFQ(s)",
                    )
                )

                if not rfqs:
                    filter_str = ", ".join(f"{k}='{v}'" for k, v in params.items() if v is not None)
                    sections.append(
                        f"🔍 No RFQs found matching criteria ({filter_str or 'all'})."
                    )
                else:
                    lines = [f"📋 **SLD RFQ Results** ({len(rfqs)} found):", ""]
                    for r in rfqs:
                        status_badge = {
                            "open": "🟡 OPEN",
                            "quoted": "🔵 QUOTED",
                            "traded": "🟢 TRADED",
                            "expired": "⚪ EXPIRED",
                            "rejected": "🔴 REJECTED",
                        }.get(r.status, r.status.upper())

                        lines.append(f"**{r.rfq_id}** — {r.product_name} [{status_badge}]")
                        lines.append(f"  • **ISIN / ID:** `{r.isin}` | `{r.product_id}`")
                        lines.append(
                            f"  • **Type:** {r.product_type} | **Volume:** {r.currency} {r.nominal:,.0f} | **Client:** {r.client}"
                        )
                        lines.append(f"  • **Underlyings:** {', '.join(r.underlyings)}")

                        if r.status == "traded":
                            lines.append(
                                f"  • **Execution:** Traded with **{r.traded_with}** at {r.traded_price_pct:.2f}%"
                            )
                        elif r.best_quote:
                            lines.append(
                                f"  • **Best Quote:** **{r.best_quote.issuer}** @ {r.best_quote.price_pct:.2f}% "
                                f"(Coupon: {r.best_quote.coupon_pct_pa:.2f}% p.a.)"
                            )
                            if len(r.quotes) > 1:
                                other_issuers = [q.issuer for q in r.quotes if q.issuer != r.best_quote.issuer]
                                lines.append(f"  • **Other Quotes:** {', '.join(other_issuers)} ({len(r.quotes)} total)")
                        elif r.status == "open":
                            lines.append("  • **Quotes:** Awaiting pricing from market makers")

                        lines.append("")
                    sections.append("\n".join(lines).strip())

        # Construct final interpreted reply
        header_blocks = []
        if records:
            call_summaries = []
            for rec in records:
                param_strs = [f"{k}={v!r}" for k, v in rec.parameters.items() if v is not None]
                call_summaries.append(f"`{rec.tool}({', '.join(param_strs)})`")
            header_blocks.append(f"🔧 **Tools Called:** {' & '.join(call_summaries)}\n")

        final_content = "\n\n---\n\n".join(filter(None, [("\n".join(header_blocks) if header_blocks else None)] + sections))

        if not final_content.strip():
            final_content = (
                f"I received your inquiry: {clean_text!r}. "
                "You can query SLD RFQs (`get_rfqs`), product underlyings (`get_underlyings_of_product`), "
                "or fee schedules (`get_fees_of_product`)."
            )

        return final_content, records

    async def generate_reply(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> str:
        """Backward-compatible reply generator returning string text."""
        reply, _ = await self.execute_and_interpret(message=message, history=history)
        return reply


dummy_llm_service = DummyLLMService()
