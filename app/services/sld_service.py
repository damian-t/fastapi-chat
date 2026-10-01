import csv
import json
from pathlib import Path
from typing import Any

from app.models.sld import (
    RFQ,
    RFQQuote,
    Underlying,
    ProductUnderlyingsResponse,
    ProductFeesResponse,
)

DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "rfq_products.csv"


class SLDService:
    """Mock SLD Service providing structured product RFQs, underlyings, and fees loaded from CSV."""

    def __init__(self, csv_path: Path | str | None = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
        self._rfqs: list[dict[str, Any]] = []
        self._products: dict[str, dict[str, Any]] = {}
        self._load_from_csv(self.csv_path)

    def _load_from_csv(self, csv_file: Path) -> None:
        """Load RFQs, underlyings, and fees from CSV."""
        if not csv_file.exists():
            raise FileNotFoundError(f"Mock dataset CSV not found at: {csv_file}")

        self._rfqs.clear()
        self._products.clear()

        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rfq_id = row["rfq_id"]
                product_id = row["product_id"]
                isin = row["isin"]
                product_name = row["product_name"]
                product_type = row["product_type"]
                basket_type = row.get("basket_type", "Worst-of Basket")
                status = row["status"]
                currency = row["currency"]
                nominal = float(row["nominal"])
                client = row["client"]
                created_at = row["created_at"]
                expires_at = row["expires_at"]
                traded_with = row["traded_with"] if row.get("traded_with") else None
                traded_price_pct = (
                    float(row["traded_price_pct"])
                    if row.get("traded_price_pct") and row["traded_price_pct"].strip()
                    else None
                )

                # Parse quotes
                quotes_raw = json.loads(row["quotes"]) if row.get("quotes") else []
                quotes = [
                    RFQQuote(
                        issuer=q["issuer"],
                        price_pct=float(q["price_pct"]),
                        coupon_pct_pa=float(q["coupon_pct_pa"]),
                        timestamp=q["timestamp"],
                        valid_until=q["valid_until"],
                    )
                    for q in quotes_raw
                ]

                # Best quote
                best_quote = None
                if row.get("best_quote") and row["best_quote"].strip():
                    bq_data = json.loads(row["best_quote"])
                    best_quote = RFQQuote(
                        issuer=bq_data["issuer"],
                        price_pct=float(bq_data["price_pct"]),
                        coupon_pct_pa=float(bq_data["coupon_pct_pa"]),
                        timestamp=bq_data["timestamp"],
                        valid_until=bq_data["valid_until"],
                    )

                # Parse underlyings
                underlyings_raw = json.loads(row["underlyings"]) if row.get("underlyings") else []
                underlying_objs = []
                underlying_tickers = []
                for u in underlyings_raw:
                    u_obj = Underlying(
                        name=u["name"],
                        ticker=u["ticker"],
                        asset_class=u["asset_class"],
                        currency=u["currency"],
                        spot_price=float(u["spot_price"]),
                        strike_level_pct=float(u["strike_level_pct"]),
                        barrier_level_pct=(
                            float(u["barrier_level_pct"])
                            if u.get("barrier_level_pct") is not None
                            else None
                        ),
                        current_price=float(u["current_price"]),
                        performance_pct=float(u["performance_pct"]),
                        barrier_hit=bool(u.get("barrier_hit", False)),
                        distance_to_barrier_pct=(
                            float(u["distance_to_barrier_pct"])
                            if u.get("distance_to_barrier_pct") is not None
                            else None
                        ),
                    )
                    underlying_objs.append(u_obj)
                    underlying_tickers.append(u["ticker"])

                # Parse fees
                dist_fee = float(row.get("distribution_fee_pct", 0.0))
                struct_fee = float(row.get("structuring_fee_pct", 0.0))
                mgmt_fee = float(row.get("management_fee_pct_pa", 0.0))
                exch_fee = float(row.get("exchange_fee_pct", 0.0))
                total_fee = float(row.get("total_fee_pct", dist_fee + struct_fee + mgmt_fee + exch_fee))
                fee_desc = row.get("fee_description", "")

                fees_dict = {
                    "distribution_fee_pct": dist_fee,
                    "structuring_fee_pct": struct_fee,
                    "management_fee_pct_pa": mgmt_fee,
                    "exchange_fee_pct": exch_fee,
                    "total_fee_pct": total_fee,
                    "description": fee_desc,
                }

                rfq_dict = {
                    "rfq_id": rfq_id,
                    "product_id": product_id,
                    "isin": isin,
                    "product_name": product_name,
                    "product_type": product_type,
                    "status": status,
                    "currency": currency,
                    "nominal": nominal,
                    "client": client,
                    "underlyings": underlying_tickers,
                    "quotes": [q.model_dump() for q in quotes],
                    "best_quote": best_quote.model_dump() if best_quote else None,
                    "traded_with": traded_with,
                    "traded_price_pct": traded_price_pct,
                    "created_at": created_at,
                    "expires_at": expires_at,
                }
                self._rfqs.append(rfq_dict)

                self._products[product_id] = {
                    "rfq_id": rfq_id,
                    "product_id": product_id,
                    "isin": isin,
                    "product_name": product_name,
                    "product_type": product_type,
                    "basket_type": basket_type,
                    "currency": currency,
                    "nominal": nominal,
                    "underlyings": [u.model_dump() for u in underlying_objs],
                    "fees": fees_dict,
                }

    def _resolve_product_id(self, identifier: str) -> str | None:
        """Resolve a product ID from product_id, isin, or rfq_id."""
        clean = identifier.strip().upper()

        if clean in self._products:
            return clean

        for pid, data in self._products.items():
            if data.get("isin", "").upper() == clean:
                return pid

        for rfq in self._rfqs:
            if rfq["rfq_id"].upper() == clean or rfq.get("isin", "").upper() == clean:
                return rfq["product_id"]

        for pid in self._products:
            if clean in pid:
                return pid

        return None

    def get_rfqs(
        self,
        rfq_id: str | None = None,
        status: str | None = None,
        issuer: str | None = None,
        product_type: str | None = None,
        currency: str | None = None,
        client: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[RFQ]:
        """Fetch RFQs matching specified filter criteria.

        Args:
            rfq_id: Filter by exact or partial RFQ ID, ISIN, or product ID
            status: Filter by status ('open', 'quoted', 'traded', 'expired', 'rejected')
            issuer: Filter by quoted or traded issuer (e.g. 'ZKB', 'UBS', 'Vontobel', 'BNP Paribas')
            product_type: Filter by product structure type
            currency: Filter by currency (e.g. 'CHF', 'USD', 'EUR')
            client: Filter by client name
            limit: Maximum number of RFQs to return
            offset: Number of RFQs to skip
        """
        results: list[dict[str, Any]] = self._rfqs

        if rfq_id:
            rfq_clean = rfq_id.strip().upper()
            results = [
                r for r in results
                if rfq_clean in r["rfq_id"].upper()
                or rfq_clean in r.get("isin", "").upper()
                or rfq_clean in r.get("product_id", "").upper()
            ]

        if status:
            stat_clean = status.strip().lower()
            results = [r for r in results if r["status"].lower() == stat_clean]

        if currency:
            curr_clean = currency.strip().upper()
            results = [r for r in results if r["currency"].upper() == curr_clean]

        if product_type:
            pt_clean = product_type.strip().lower()
            results = [r for r in results if pt_clean in r["product_type"].lower()]

        if client:
            client_clean = client.strip().lower()
            results = [r for r in results if client_clean in r["client"].lower()]

        if issuer:
            iss_clean = issuer.strip().lower()
            filtered = []
            for r in results:
                if r.get("traded_with") and iss_clean in r["traded_with"].lower():
                    filtered.append(r)
                    continue
                quote_issuers = [q["issuer"].lower() for q in r.get("quotes", [])]
                if any(iss_clean in qi for qi in quote_issuers):
                    filtered.append(r)
            results = filtered

        paginated = results[offset : offset + limit] if limit else results[offset:]
        return [RFQ(**r) for r in paginated]

    get_rfq = get_rfqs

    def get_underlyings_of_product(self, product_id: str) -> ProductUnderlyingsResponse:
        """Fetch underlying assets and parameters for a specific product or RFQ.

        Args:
            product_id: Product ID (e.g. 'PRD-101'), ISIN ('CH1261564201'), or RFQ ID ('RFQ-101')
        """
        resolved_id = self._resolve_product_id(product_id)
        if not resolved_id or resolved_id not in self._products:
            raise ValueError(f"Product '{product_id}' not found in SLD database.")

        pdata = self._products[resolved_id]
        underlying_objs = [Underlying(**u) for u in pdata["underlyings"]]

        return ProductUnderlyingsResponse(
            product_id=resolved_id,
            isin=pdata["isin"],
            product_name=pdata["product_name"],
            basket_type=pdata["basket_type"],
            underlyings=underlying_objs,
        )

    get_underlyings_ofproducts = get_underlyings_of_product

    def get_fees_of_product(
        self, product_id: str, fee_type: str | None = None
    ) -> ProductFeesResponse:
        """Fetch fee structure for a specific structured product or RFQ.

        Args:
            product_id: Product ID (e.g. 'PRD-101'), ISIN ('CH1261564201'), or RFQ ID ('RFQ-101')
            fee_type: Optional fee category filter (e.g. 'distribution', 'structuring', 'all')
        """
        resolved_id = self._resolve_product_id(product_id)
        if not resolved_id or resolved_id not in self._products:
            raise ValueError(f"Product '{product_id}' not found in SLD database.")

        pdata = self._products[resolved_id]
        fdata = pdata["fees"]
        nominal = pdata["nominal"]
        currency = pdata["currency"]
        total_fee_pct = fdata["total_fee_pct"]
        monetary_amount = round(nominal * (total_fee_pct / 100.0), 2)

        return ProductFeesResponse(
            product_id=resolved_id,
            isin=pdata["isin"],
            product_name=pdata["product_name"],
            currency=currency,
            nominal=nominal,
            distribution_fee_pct=fdata["distribution_fee_pct"],
            structuring_fee_pct=fdata["structuring_fee_pct"],
            management_fee_pct_pa=fdata["management_fee_pct_pa"],
            exchange_fee_pct=fdata["exchange_fee_pct"],
            total_fee_pct=total_fee_pct,
            estimated_monetary_amount=monetary_amount,
            description=fdata["description"],
        )


sld_service = SLDService()
