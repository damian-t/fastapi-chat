import csv
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

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
    ) -> list[Product]:
        """Fetch structured products / RFQs from SLD matching search period or security identifiers.

        Inputs (all optional):
            start_date: Start date of search period.
            end_date: End date for search period.
            isin: Security identifier of the product which was quoted.
            valor: Security identifier of the product which was quoted.

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

        return [r["_product"] for r in filtered_records]

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


sld_service = SLDService()
