import csv
import json
import re
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
                self._id_mappings[isin.upper()] = product_id_str

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
                    valor=None,
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
        rfq_id: str | int | None = None,
        status: str | None = None,
        issuer: str | None = None,
        product_type: str | None = None,
        currency: str | None = None,
        client: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Product]:
        """Fetch products matching specified filter criteria.

        Returns a list of Product dataclasses.
        """
        filtered_records = self._raw_records

        if rfq_id is not None:
            clean = str(rfq_id).strip().upper()
            filtered_records = [
                r for r in filtered_records
                if clean in r["rfq_id"].upper()
                or clean in r.get("isin", "").upper()
                or clean in r.get("product_id", "").upper()
                or clean in str(self._extract_int_id(r.get("product_id")))
            ]

        if status:
            stat_clean = status.strip().lower()
            filtered_records = [
                r for r in filtered_records if r.get("status", "").lower() == stat_clean
            ]

        if currency:
            curr_clean = currency.strip().upper()
            filtered_records = [
                r for r in filtered_records if r.get("currency", "").upper() == curr_clean
            ]

        if product_type:
            pt_clean = product_type.strip().lower()
            filtered_records = [
                r for r in filtered_records if pt_clean in r.get("product_type", "").lower()
            ]

        if client:
            client_clean = client.strip().lower()
            filtered_records = [
                r for r in filtered_records if client_clean in r.get("client", "").lower()
            ]

        if issuer:
            iss_clean = issuer.strip().lower()
            filtered = []
            for r in filtered_records:
                if r.get("traded_with") and iss_clean in r["traded_with"].lower():
                    filtered.append(r)
                    continue
                quotes = json.loads(r.get("quotes", "[]")) if r.get("quotes") else []
                quote_issuers = [q.get("issuer", "").lower() for q in quotes]
                if any(iss_clean in qi for qi in quote_issuers):
                    filtered.append(r)
            filtered_records = filtered

        paginated = filtered_records[offset : offset + limit] if limit else filtered_records[offset:]
        return [r["_product"] for r in paginated]

    get_products = get_rfqs
    get_rfq = get_rfqs

    def get_underlyings_of_product(self, product_id: str | int) -> list[Underlying]:
        """Fetch underlying Bloomberg tickers for a specific product.

        Returns a list of Underlying dataclasses.
        """
        key = self._resolve_key(product_id)
        if not key or key not in self._underlyings_by_product_id:
            raise ValueError(f"Product '{product_id}' not found in SLD database.")
        return list(self._underlyings_by_product_id[key])

    get_underlying_of_product = get_underlyings_of_product
    get_underlyings_for_product = get_underlyings_of_product
    get_underlyings_ofproducts = get_underlyings_of_product

    def get_fees_of_product(
        self, product_id: str | int, fee_type: str | None = None
    ) -> list[Fee]:
        """Fetch fee schedule for a specific structured product.

        Returns a list of Fee dataclasses.
        """
        key = self._resolve_key(product_id)
        if not key or key not in self._fees_by_product_id:
            raise ValueError(f"Product '{product_id}' not found in SLD database.")

        fees = self._fees_by_product_id[key]
        if fee_type:
            ft_clean = fee_type.strip().lower()
            if ft_clean != "all":
                fees = [f for f in fees if ft_clean in f.feeType.lower() or ft_clean in f.name.lower()]

        return list(fees)

    get_fees_for_product = get_fees_of_product


sld_service = SLDService()
