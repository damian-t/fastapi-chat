import csv
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from app.models.sld import (
    Underlying,
    ProductGeneral,
    ProductPricing,
    Fee,
    ProductFees,
    Product,
)

DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "rfq_products.csv"


def _parse_search_date(val: str | date | datetime | None, is_end: bool = False) -> datetime | None:
    """Parse string/date/datetime into timezone-aware datetime for range queries."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, date):
        if is_end:
            return datetime(val.year, val.month, val.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return datetime(val.year, val.month, val.day, 0, 0, 0, tzinfo=timezone.utc)

    val_str = str(val).strip()
    if not val_str:
        return None
    if len(val_str) == 10 and "T" not in val_str and " " not in val_str:
        try:
            d = date.fromisoformat(val_str)
            if is_end:
                return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
            return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(val_str)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class SLDService:
    """SLD Service providing structured products, underlyings, and fees loaded from dataset."""

    def __init__(self, csv_path: Path | str | None = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
        self._products_list: list[Product] = []
        self._raw_records: list[dict[str, Any]] = []
        self._products_by_id: dict[str, Product] = {}
        self._fees_by_product_id: dict[str, list[Fee]] = {}
        self._underlyings_by_product_id: dict[str, list[Underlying]] = {}
        self._id_mappings: dict[str, str] = {}
        self._load_from_csv(self.csv_path)

    def _extract_int_id(self, val: str | int | None) -> int:
        if val is None:
            return 0
        if isinstance(val, int):
            return val
        digits = "".join(c for c in str(val) if c.isdigit())
        return int(digits) if digits else 0

    def _load_from_csv(self, csv_file: Path) -> None:
        """Load products, underlyings, and fees from CSV dataset."""
        if not csv_file.exists():
            raise FileNotFoundError(f"Mock dataset CSV not found at: {csv_file}")

        self._products_list.clear()
        self._raw_records.clear()
        self._products_by_id.clear()
        self._fees_by_product_id.clear()
        self._underlyings_by_product_id.clear()
        self._id_mappings.clear()

        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rfq_id = row["rfq_id"]
                product_id_str = row["product_id"]
                int_id = self._extract_int_id(product_id_str)
                isin = row["isin"]
                valor = row.get("valor")
                if not valor:
                    valor = str(126156000 + int_id) if int_id else None

                product_name = row["product_name"]
                product_type = row["product_type"]
                currency = row["currency"]
                nominal = float(row["nominal"]) if row.get("nominal") else 100000.0
                client = row.get("client")
                status = row.get("status", "open")

                # Map various identifiers to product_id_str
                self._id_mappings[str(int_id)] = product_id_str
                self._id_mappings[product_id_str.upper()] = product_id_str
                self._id_mappings[rfq_id.upper()] = product_id_str
                if isin:
                    self._id_mappings[isin.upper()] = product_id_str
                if valor:
                    self._id_mappings[str(valor).upper()] = product_id_str

                # Parse underlyings
                underlyings_raw = json.loads(row["underlyings"]) if row.get("underlyings") else []
                underlying_objs: list[Underlying] = []
                for u in underlyings_raw:
                    ticker = u.get("ticker") or u.get("underlyingBloombergTicker") or str(u)
                    underlying_objs.append(Underlying(underlyingBloombergTicker=ticker))

                if not underlying_objs and row.get("underlying_tickers"):
                    for t in row["underlying_tickers"].split(";"):
                        t_clean = t.strip()
                        if t_clean:
                            underlying_objs.append(Underlying(underlyingBloombergTicker=t_clean))

                self._underlyings_by_product_id[product_id_str] = underlying_objs

                # Parse fees
                dist_fee = float(row.get("distribution_fee_pct", 0.5))
                struct_fee = float(row.get("structuring_fee_pct", 0.25))
                mgmt_fee = float(row.get("management_fee_pct_pa", 0.0))
                exch_fee = float(row.get("exchange_fee_pct", 0.05))
                total_entry = Decimal(str(round(dist_fee + struct_fee + exch_fee, 4)))

                fees_list = [
                    Fee(
                        name="Distribution Fee",
                        amount=dist_fee,
                        feeType="distribution",
                        maturityType="at_issue",
                        isPricingRelevant=True,
                    ),
                    Fee(
                        name="Structuring Fee",
                        amount=struct_fee,
                        feeType="structuring",
                        maturityType="at_issue",
                        isPricingRelevant=True,
                    ),
                    Fee(
                        name="Management Fee",
                        amount=mgmt_fee,
                        feeType="management",
                        maturityType="recurring",
                        isPricingRelevant=False,
                    ),
                    Fee(
                        name="Exchange Fee",
                        amount=exch_fee,
                        feeType="exchange",
                        maturityType="at_issue",
                        isPricingRelevant=True,
                    ),
                ]
                self._fees_by_product_id[product_id_str] = fees_list

                # Fair value pricing
                fair_val = 100.0
                if row.get("traded_price_pct") and row["traded_price_pct"].strip():
                    fair_val = float(row["traded_price_pct"])
                elif row.get("best_quote") and row["best_quote"].strip():
                    try:
                        bq = json.loads(row["best_quote"])
                        fair_val = float(bq.get("price_pct", 100.0))
                    except Exception:
                        pass

                general = ProductGeneral(
                    productId=int_id,
                    productUuid=product_id_str,
                    partyIdentifierCustodian=None,
                    partyIdentifierClient=client,
                    productType=product_type,
                    productAmount=nominal,
                    productQuotationType="Percentage",
                    currency=currency,
                    initialFixingType="Spot",
                    initialFixingDate=row.get("created_at"),
                    finalFixingDate=row.get("expires_at"),
                    issueDate=row.get("created_at"),
                    finalPaymentDate=row.get("expires_at"),
                    underlyingList=underlying_objs,
                    dayCountFraction="30/360",
                    settlementType="Cash",
                    finalValuationCutOffTime="17:00",
                    finalValuationCutOffLocation="Zurich",
                    productName=product_name,
                    valor=str(valor) if valor else None,
                    isin=isin,
                )

                pricing = ProductPricing(fairValue=Decimal(str(round(fair_val, 4))))
                fees = ProductFees(entryCosts=total_entry, _product_id=int_id)

                quotes_raw = json.loads(row["quotes"]) if row.get("quotes") else []

                product = Product(
                    productGeneral=general,
                    productPricing=pricing,
                    productFees=fees,
                    _status=status,
                    _quotes=quotes_raw,
                )

                self._products_list.append(product)
                self._products_by_id[product_id_str] = product

                raw_record = dict(row)
                raw_record["valor"] = str(valor) if valor else None
                raw_record["_created_dt"] = _parse_search_date(row.get("created_at"))
                raw_record["_product"] = product
                self._raw_records.append(raw_record)

    def _resolve_key(self, identifier: str | int) -> str | None:
        """Resolve a lookup key to the primary product_id_str."""
        if identifier is None:
            return None
        key = str(identifier).strip().upper()
        if key in self._id_mappings:
            return self._id_mappings[key]

        # Try numeric string
        digits = "".join(c for c in key if c.isdigit())
        if digits and digits in self._id_mappings:
            return self._id_mappings[digits]

        for k, v in self._id_mappings.items():
            if key in k:
                return v

        return None

    def get_rfqs(
        self,
        start_date: str | date | datetime | None = None,
        end_date: str | date | datetime | None = None,
        isin: str | None = None,
        valor: str | int | None = None,
        currency: str | None = None,
        status: str | None = None,
        issuer: str | None = None,
        product_type: str | None = None,
        underlying: str | None = None,
        rfq_id: str | int | None = None,
        client: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Product]:
        """Fetch structured products / RFQs from SLD matching search period, identifiers, or subset filters.

        Inputs (all optional):
            start_date: Start date of search period.
            end_date: End date for search period.
            isin: Security identifier of the product which was quoted.
            valor: Security identifier of the product which was quoted.
            currency: Currency code filter (e.g. CHF, USD, EUR).
            status: Lifecycle status (e.g. open, quoted, traded, expired, rejected).
            issuer: Issuer bank filter (e.g. ZKB, UBS, Vontobel, BNP Paribas).
            product_type: Product structure filter (e.g. Barrier Reverse Convertible).
            underlying: Underlying Bloomberg ticker symbol or keyword filter (e.g. NESN, AAPL).
            rfq_id: RFQ identifier or product ID (e.g. RFQ-101, PRD-101).
            client: Client name filter.
            limit: Maximum number of products to return (pagination).
            offset: Number of products to skip (pagination).

        Returns a list of Product dataclasses.
        """
        filtered_records = self._raw_records

        if start_date is not None:
            start_dt = _parse_search_date(start_date, is_end=False)
            if start_dt is not None:
                filtered_records = [
                    r for r in filtered_records
                    if r.get("_created_dt") is not None and r["_created_dt"] >= start_dt
                ]

        if end_date is not None:
            end_dt = _parse_search_date(end_date, is_end=True)
            if end_dt is not None:
                filtered_records = [
                    r for r in filtered_records
                    if r.get("_created_dt") is not None and r["_created_dt"] <= end_dt
                ]

        if isin is not None:
            clean_isin = str(isin).strip().upper()
            filtered_records = [
                r for r in filtered_records
                if clean_isin == (r.get("isin") or "").strip().upper()
                or clean_isin == (r["_product"].productGeneral.isin or "").strip().upper()
            ]

        if valor is not None:
            clean_valor = str(valor).strip().upper()
            filtered_records = [
                r for r in filtered_records
                if clean_valor == str(r.get("valor") or "").strip().upper()
                or clean_valor == str(r["_product"].productGeneral.valor or "").strip().upper()
            ]

        if rfq_id is not None:
            clean_rfq = str(rfq_id).strip().upper()
            filtered_records = [
                r for r in filtered_records
                if clean_rfq == str(r.get("rfq_id") or "").strip().upper()
                or clean_rfq == str(r.get("product_id") or "").strip().upper()
                or clean_rfq == str(self._extract_int_id(r.get("product_id")))
                or clean_rfq == (r.get("isin") or "").strip().upper()
                or clean_rfq == str(r.get("valor") or "").strip().upper()
            ]

        if status is not None:
            clean_status = str(status).strip().lower()
            filtered_records = [
                r for r in filtered_records
                if clean_status == (r.get("status") or "").strip().lower()
                or clean_status == (r["_product"].status or "").strip().lower()
            ]

        if currency is not None:
            clean_curr = str(currency).strip().upper()
            filtered_records = [
                r for r in filtered_records
                if clean_curr == (r.get("currency") or "").strip().upper()
                or clean_curr == (r["_product"].currency or "").strip().upper()
            ]

        if issuer is not None:
            clean_issuer = str(issuer).strip().lower()
            matching = []
            for r in filtered_records:
                if r.get("traded_with") and clean_issuer in str(r["traded_with"]).lower():
                    matching.append(r)
                    continue
                quotes = r["_product"].quotes or (json.loads(r.get("quotes", "[]")) if r.get("quotes") else [])
                quote_issuers = [str(q.get("issuer", "")).lower() for q in quotes if isinstance(q, dict)]
                if any(clean_issuer in qi for qi in quote_issuers):
                    matching.append(r)
            filtered_records = matching

        if product_type is not None:
            clean_pt = str(product_type).strip().lower()
            filtered_records = [
                r for r in filtered_records
                if clean_pt in (r.get("product_type") or "").strip().lower()
                or clean_pt in (r["_product"].productGeneral.productType or "").strip().lower()
            ]

        if underlying is not None:
            clean_und = str(underlying).strip().upper()
            matching = []
            for r in filtered_records:
                tickers = [
                    (u.underlyingBloombergTicker or "").upper()
                    for u in (r["_product"].productGeneral.underlyingList or [])
                ]
                raw_und = str(r.get("underlying_tickers") or "").upper()
                if any(clean_und in t for t in tickers) or clean_und in raw_und:
                    matching.append(r)
            filtered_records = matching

        if client is not None:
            clean_client = str(client).strip().lower()
            filtered_records = [
                r for r in filtered_records
                if clean_client in (r.get("client") or "").strip().lower()
                or clean_client in (r["_product"].productGeneral.partyIdentifierClient or "").strip().lower()
            ]

        offset_val = max(0, offset) if offset else 0
        if limit is not None:
            limit_val = max(1, limit)
            paginated = filtered_records[offset_val : offset_val + limit_val]
        else:
            paginated = filtered_records[offset_val:]

        return [r["_product"] for r in paginated]

    get_products = get_rfqs
    get_rfq = get_rfqs

    def get_underlyings_for_product(self, product_id: str | int) -> list[Underlying]:
        """Fetch underlying Bloomberg tickers for a specific structured product.

        Parameters:
            product_id: Mandatory product identifier (product ID, valor, ISIN, or RFQ ID).

        Returns a list of Underlying dataclasses.
        """
        if product_id is None or (isinstance(product_id, str) and not product_id.strip()):
            raise ValueError("product_id is mandatory.")

        key = self._resolve_key(product_id)
        if not key or key not in self._underlyings_by_product_id:
            raise ValueError(f"Product '{product_id}' not found in SLD database.")

        return list(self._underlyings_by_product_id[key])

    get_underlying_of_product = get_underlyings_for_product
    get_underlyings_of_product = get_underlyings_for_product
    get_underlyings_ofproducts = get_underlyings_for_product

    def get_fees_for_product(self, product_id: str | int) -> list[Fee]:
        """Fetch fee schedule for a specific structured product.

        Parameters:
            product_id: Mandatory product identifier (product ID, valor, ISIN, or RFQ ID).

        Returns a list of Fee dataclasses.
        """
        if product_id is None or (isinstance(product_id, str) and not product_id.strip()):
            raise ValueError("product_id is mandatory.")

        key = self._resolve_key(product_id)
        if not key or key not in self._fees_by_product_id:
            raise ValueError(f"Product '{product_id}' not found in SLD database.")

        return list(self._fees_by_product_id[key])

    get_fees_of_product = get_fees_for_product

    def _default_rfq_mapper(self, batch: list[Product], operation: str = "summary") -> dict[str, Any]:
        """Map step: aggregate metrics for a batch/page of products."""
        count = len(batch)
        status_counts: dict[str, int] = {}
        currency_volumes: dict[str, float] = {}
        currency_counts: dict[str, int] = {}
        issuer_volumes: dict[str, float] = {}
        issuer_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        underlying_counts: dict[str, int] = {}

        total_nominal = 0.0
        fair_value_sum = 0.0
        fair_value_count = 0
        fair_value_min = float("inf")
        fair_value_max = float("-inf")

        entry_costs_sum = 0.0
        entry_costs_count = 0
        entry_costs_min = float("inf")
        entry_costs_max = float("-inf")

        top_by_volume: list[dict[str, Any]] = []

        for p in batch:
            gen = getattr(p, "productGeneral", None) or p
            pricing = getattr(p, "productPricing", None)
            fees = getattr(p, "productFees", None)

            status = getattr(p, "_status", None) or getattr(p, "status", "open")
            status_counts[status] = status_counts.get(status, 0) + 1

            curr = getattr(gen, "currency", None) or getattr(p, "currency", "CHF")
            nominal = getattr(gen, "productAmount", None) or getattr(p, "nominal", 0.0) or 0.0
            try:
                nominal_val = float(nominal)
            except (ValueError, TypeError):
                nominal_val = 0.0

            currency_volumes[curr] = currency_volumes.get(curr, 0.0) + nominal_val
            currency_counts[curr] = currency_counts.get(curr, 0) + 1
            total_nominal += nominal_val

            ptype = getattr(gen, "productType", None) or getattr(p, "product_type", "Structured Product")
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

            # Underlyings
            und_list = getattr(gen, "underlyingList", None) or getattr(p, "underlyings", []) or []
            for u in und_list:
                ticker = getattr(u, "underlyingBloombergTicker", None) or (u.get("underlyingBloombergTicker") if isinstance(u, dict) else str(u))
                if ticker:
                    underlying_counts[ticker] = underlying_counts.get(ticker, 0) + 1

            # Quotes / Issuers
            quotes = getattr(p, "_quotes", []) or getattr(p, "quotes", []) or []
            if quotes:
                for q in quotes:
                    iss = q.get("issuer") or q.get("issuer_name") or "Unknown"
                    issuer_counts[iss] = issuer_counts.get(iss, 0) + 1
                    issuer_volumes[iss] = issuer_volumes.get(iss, 0.0) + nominal_val
            else:
                iss = getattr(p, "issuer", None) or "Quoted Bank"
                issuer_counts[iss] = issuer_counts.get(iss, 0) + 1
                issuer_volumes[iss] = issuer_volumes.get(iss, 0.0) + nominal_val

            # Fair value pricing
            fv = getattr(pricing, "fairValue", None) if pricing else None
            if fv is not None:
                try:
                    fv_flt = float(fv)
                    fair_value_sum += fv_flt
                    fair_value_count += 1
                    if fv_flt < fair_value_min:
                        fair_value_min = fv_flt
                    if fv_flt > fair_value_max:
                        fair_value_max = fv_flt
                except (ValueError, TypeError):
                    pass

            # Entry costs
            ec = getattr(fees, "entryCosts", None) if fees else None
            if ec is not None:
                try:
                    ec_flt = float(ec)
                    entry_costs_sum += ec_flt
                    entry_costs_count += 1
                    if ec_flt < entry_costs_min:
                        entry_costs_min = ec_flt
                    if ec_flt > entry_costs_max:
                        entry_costs_max = ec_flt
                except (ValueError, TypeError):
                    pass

            prod_id = getattr(gen, "productId", None) or getattr(p, "product_id", None)
            rfq_id = getattr(p, "rfq_id", None) or (f"RFQ-{prod_id}" if prod_id else None)
            isin = getattr(gen, "isin", None) or getattr(p, "isin", None)
            name = getattr(gen, "productName", None) or getattr(p, "product_name", None)
            top_by_volume.append({
                "rfq_id": rfq_id,
                "product_id": f"PRD-{prod_id}" if prod_id else None,
                "isin": isin,
                "name": name,
                "currency": curr,
                "nominal": nominal_val,
                "status": status,
            })

        top_by_volume.sort(key=lambda x: x["nominal"], reverse=True)
        top_by_volume = top_by_volume[:5]

        return {
            "batch_count": count,
            "total_nominal": round(total_nominal, 2),
            "status_counts": status_counts,
            "currency_volumes": {k: round(v, 2) for k, v in currency_volumes.items()},
            "currency_counts": currency_counts,
            "issuer_volumes": {k: round(v, 2) for k, v in issuer_volumes.items()},
            "issuer_counts": issuer_counts,
            "type_counts": type_counts,
            "underlying_counts": underlying_counts,
            "fair_value_stats": {
                "sum": fair_value_sum,
                "count": fair_value_count,
                "min": fair_value_min if fair_value_count > 0 else None,
                "max": fair_value_max if fair_value_count > 0 else None,
            },
            "entry_costs_stats": {
                "sum": entry_costs_sum,
                "count": entry_costs_count,
                "min": entry_costs_min if entry_costs_count > 0 else None,
                "max": entry_costs_max if entry_costs_count > 0 else None,
            },
            "top_by_volume": top_by_volume,
        }

    def _default_rfq_reducer(self, accum: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
        """Reduce step: accumulate batch-level metrics into consolidated summary."""
        accum["batch_count"] += batch["batch_count"]
        accum["total_nominal"] = round(accum["total_nominal"] + batch["total_nominal"], 2)

        for k, v in batch["status_counts"].items():
            accum["status_counts"][k] = accum["status_counts"].get(k, 0) + v

        for k, v in batch["currency_volumes"].items():
            accum["currency_volumes"][k] = round(accum["currency_volumes"].get(k, 0.0) + v, 2)

        for k, v in batch["currency_counts"].items():
            accum["currency_counts"][k] = accum["currency_counts"].get(k, 0) + v

        for k, v in batch["issuer_volumes"].items():
            accum["issuer_volumes"][k] = round(accum["issuer_volumes"].get(k, 0.0) + v, 2)

        for k, v in batch["issuer_counts"].items():
            accum["issuer_counts"][k] = accum["issuer_counts"].get(k, 0) + v

        for k, v in batch["type_counts"].items():
            accum["type_counts"][k] = accum["type_counts"].get(k, 0) + v

        for k, v in batch["underlying_counts"].items():
            accum["underlying_counts"][k] = accum["underlying_counts"].get(k, 0) + v

        # Fair value stats
        b_fv = batch["fair_value_stats"]
        a_fv = accum["fair_value_stats"]
        a_fv["sum"] += b_fv["sum"]
        a_fv["count"] += b_fv["count"]
        if b_fv["min"] is not None:
            a_fv["min"] = b_fv["min"] if a_fv["min"] is None else min(a_fv["min"], b_fv["min"])
        if b_fv["max"] is not None:
            a_fv["max"] = b_fv["max"] if a_fv["max"] is None else max(a_fv["max"], b_fv["max"])

        # Entry costs stats
        b_ec = batch["entry_costs_stats"]
        a_ec = accum["entry_costs_stats"]
        a_ec["sum"] += b_ec["sum"]
        a_ec["count"] += b_ec["count"]
        if b_ec["min"] is not None:
            a_ec["min"] = b_ec["min"] if a_ec["min"] is None else min(a_ec["min"], b_ec["min"])
        if b_ec["max"] is not None:
            a_ec["max"] = b_ec["max"] if a_ec["max"] is None else max(a_ec["max"], b_ec["max"])

        # Merge top by volume
        merged_top = accum["top_by_volume"] + batch["top_by_volume"]
        seen = set()
        deduped = []
        for item in sorted(merged_top, key=lambda x: x["nominal"], reverse=True):
            key = item.get("rfq_id") or item.get("isin") or item.get("name")
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        accum["top_by_volume"] = deduped[:5]

        return accum

    def batch_map_reduce_rfqs(
        self,
        filter_params: dict[str, Any] | None = None,
        batch_size: int = 500,
        operation: str = "summary",
        mapper: Callable[[list[Product]], dict[str, Any]] | None = None,
        reducer: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute server-side batch map-reduce over RFQs using page-by-page traversal.

        Default batch page size is 500 records.
        Processes arbitrary populations (up to 10k+ products) within server memory
        and returns a bounded, compact summary to protect LLM context windows.
        """
        if batch_size <= 0:
            batch_size = 500

        offset = 0
        batches_processed = 0
        total_records = 0
        accumulated_result: dict[str, Any] | None = None

        while True:
            batch = self.get_rfqs(
                limit=batch_size,
                offset=offset,
                **(filter_params or {}),
            )
            if not batch:
                break

            batches_processed += 1
            total_records += len(batch)

            mapped_batch = mapper(batch) if mapper else self._default_rfq_mapper(batch, operation)

            if accumulated_result is None:
                accumulated_result = mapped_batch
            else:
                accumulated_result = reducer(accumulated_result, mapped_batch) if reducer else self._default_rfq_reducer(accumulated_result, mapped_batch)

            if len(batch) < batch_size:
                break

            offset += batch_size

        if accumulated_result is None:
            accumulated_result = self._default_rfq_mapper([], operation)

        fv_stats = accumulated_result.get("fair_value_stats", {})
        avg_fair_value = round(fv_stats["sum"] / fv_stats["count"], 4) if fv_stats.get("count", 0) > 0 else None

        ec_stats = accumulated_result.get("entry_costs_stats", {})
        avg_entry_costs = round(ec_stats["sum"] / ec_stats["count"], 4) if ec_stats.get("count", 0) > 0 else None

        und_counts = accumulated_result.get("underlying_counts", {})
        top_underlyings = dict(sorted(und_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        return {
            "operation": operation,
            "batch_size": batch_size,
            "batches_processed": batches_processed,
            "total_records_processed": total_records,
            "total_nominal_volume": accumulated_result.get("total_nominal", 0.0),
            "volumes_by_currency": accumulated_result.get("currency_volumes", {}),
            "counts_by_currency": accumulated_result.get("currency_counts", {}),
            "status_distribution": accumulated_result.get("status_counts", {}),
            "product_type_distribution": accumulated_result.get("type_counts", {}),
            "volumes_by_issuer": accumulated_result.get("issuer_volumes", {}),
            "counts_by_issuer": accumulated_result.get("issuer_counts", {}),
            "top_underlyings": top_underlyings,
            "average_fair_value_pct": avg_fair_value,
            "fair_value_range": {
                "min": fv_stats.get("min"),
                "max": fv_stats.get("max"),
            },
            "average_entry_costs_pct": avg_entry_costs,
            "entry_costs_range": {
                "min": ec_stats.get("min"),
                "max": ec_stats.get("max"),
            },
            "top_products_by_volume": accumulated_result.get("top_by_volume", []),
        }

    map_reduce_rfqs = batch_map_reduce_rfqs
    aggregate_rfqs = batch_map_reduce_rfqs


sld_service = SLDService()
