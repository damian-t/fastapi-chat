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
    Product,
)

DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "rfq_products.csv"


class SLDService:
    """Mock SLD Service providing data for structured product RFQs, underlyings, and fees loaded from CSV."""

    def __init__(self, csv_path: Path | str | None = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
        self._rfqs: list[dict[str, Any]] = []
        self._products: dict[str, dict[str, Any]] = {}
        self._all_underlyings: list[Underlying] = []
        self._load_from_csv(self.csv_path)

    def _load_from_csv(self, csv_file: Path) -> None:
        """Load RFQs, products, underlyings, and fee schedules from CSV file."""
        if not csv_file.exists():
            raise FileNotFoundError(f"Mock dataset CSV not found at: {csv_file}")

        self._rfqs.clear()
        self._products.clear()
        self._all_underlyings.clear()

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
                        product_id=product_id,
                        isin=isin,
                    )
                    underlying_objs.append(u_obj)
                    underlying_tickers.append(u["ticker"])
                    self._all_underlyings.append(u_obj)

                # Parse fees
                dist_fee = float(row.get("distribution_fee_pct", 0.0))
                struct_fee = float(row.get("structuring_fee_pct", 0.0))
                mgmt_fee = float(row.get("management_fee_pct_pa", 0.0))
                exch_fee = float(row.get("exchange_fee_pct", 0.0))
                total_fee = float(row.get("total_fee_pct", dist_fee + struct_fee + mgmt_fee + exch_fee))
                fee_desc = row.get("fee_description", "")
                monetary_amount = round(nominal * (total_fee / 100.0), 2)

                fees_dict = {
                    "distribution_fee_pct": dist_fee,
                    "structuring_fee_pct": struct_fee,
                    "management_fee_pct_pa": mgmt_fee,
                    "exchange_fee_pct": exch_fee,
                    "total_fee_pct": total_fee,
                    "estimated_monetary_amount": monetary_amount,
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

                product_entry = {
                    "rfq_id": rfq_id,
                    "product_id": product_id,
                    "isin": isin,
                    "product_name": product_name,
                    "product_type": product_type,
                    "basket_type": basket_type,
                    "status": status,
                    "currency": currency,
                    "nominal": nominal,
                    "client": client,
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "traded_with": traded_with,
                    "traded_price_pct": traded_price_pct,
                    "underlyings": [u.model_dump() for u in underlying_objs],
                    "fees": fees_dict,
                }
                self._products[product_id] = product_entry

    def _resolve_product_id(self, identifier: str) -> str | None:
        """Resolve a product ID from product_id, isin, or rfq_id."""
        clean = identifier.strip().upper()

        # Direct match in products
        if clean in self._products:
            return clean

        # Check ISIN
        for pid, data in self._products.items():
            if data.get("isin", "").upper() == clean:
                return pid

        # Check RFQ ID
        for rfq in self._rfqs:
            if rfq["rfq_id"].upper() == clean:
                return rfq["product_id"]
            if rfq.get("isin", "").upper() == clean:
                return rfq["product_id"]

        # Substring / fuzzy matching if applicable (e.g. "101", "PRD101")
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
        """Fetch RFQs matching specified filters.

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
                # check traded_with
                if r.get("traded_with") and iss_clean in r["traded_with"].lower():
                    filtered.append(r)
                    continue
                # check quotes
                quote_issuers = [q["issuer"].lower() for q in r.get("quotes", [])]
                if any(iss_clean in qi for qi in quote_issuers):
                    filtered.append(r)
            results = filtered

        paginated = results[offset : offset + limit] if limit else results[offset:]
        return [RFQ(**r) for r in paginated]

    def get_products(
        self,
        product_id: str | None = None,
        isin: str | None = None,
        product_type: str | None = None,
        currency: str | None = None,
        basket_type: str | None = None,
        status: str | None = None,
        client: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Product]:
        """Fetch structured products matching specified filters.

        Args:
            product_id: Exact or partial product ID
            isin: Exact or partial ISIN
            product_type: Filter by product structure type
            currency: Filter by currency (e.g. 'CHF', 'USD', 'EUR')
            basket_type: Filter by basket structure (e.g. 'Worst-of Basket')
            status: Filter by lifecycle status
            client: Filter by client name
            limit: Maximum number of products to return
            offset: Number of items to skip
        """
        results = list(self._products.values())

        if product_id:
            pid_clean = product_id.strip().upper()
            results = [p for p in results if pid_clean in p["product_id"].upper()]

        if isin:
            isin_clean = isin.strip().upper()
            results = [p for p in results if isin_clean in p["isin"].upper()]

        if product_type:
            pt_clean = product_type.strip().lower()
            results = [p for p in results if pt_clean in p["product_type"].lower()]

        if currency:
            curr_clean = currency.strip().upper()
            results = [p for p in results if p["currency"].upper() == curr_clean]

        if basket_type:
            bt_clean = basket_type.strip().lower()
            results = [p for p in results if bt_clean in p["basket_type"].lower()]

        if status:
            stat_clean = status.strip().lower()
            results = [p for p in results if p["status"].lower() == stat_clean]

        if client:
            client_clean = client.strip().lower()
            results = [p for p in results if client_clean in p["client"].lower()]

        paginated = results[offset : offset + limit] if limit else results[offset:]

        products_list: list[Product] = []
        for p in paginated:
            underlying_objs = [Underlying(**u) for u in p["underlyings"]]
            fdata = p["fees"]
            fee_obj = ProductFeesResponse(
                product_id=p["product_id"],
                isin=p["isin"],
                product_name=p["product_name"],
                currency=p["currency"],
                nominal=p["nominal"],
                distribution_fee_pct=fdata["distribution_fee_pct"],
                structuring_fee_pct=fdata["structuring_fee_pct"],
                management_fee_pct_pa=fdata["management_fee_pct_pa"],
                exchange_fee_pct=fdata["exchange_fee_pct"],
                total_fee_pct=fdata["total_fee_pct"],
                estimated_monetary_amount=fdata["estimated_monetary_amount"],
                description=fdata["description"],
            )
            products_list.append(
                Product(
                    product_id=p["product_id"],
                    isin=p["isin"],
                    rfq_id=p["rfq_id"],
                    product_name=p["product_name"],
                    product_type=p["product_type"],
                    basket_type=p["basket_type"],
                    status=p["status"],
                    currency=p["currency"],
                    nominal=p["nominal"],
                    client=p["client"],
                    created_at=p["created_at"],
                    expires_at=p["expires_at"],
                    traded_with=p.get("traded_with"),
                    traded_price_pct=p.get("traded_price_pct"),
                    underlyings=underlying_objs,
                    fees=fee_obj,
                )
            )
        return products_list

    def get_product_by_id(self, identifier: str) -> Product:
        """Fetch a single product by product ID, ISIN, or RFQ ID."""
        resolved_id = self._resolve_product_id(identifier)
        if not resolved_id or resolved_id not in self._products:
            raise ValueError(f"Product '{identifier}' not found in SLD database.")

        p = self._products[resolved_id]
        underlying_objs = [Underlying(**u) for u in p["underlyings"]]
        fdata = p["fees"]
        fee_obj = ProductFeesResponse(
            product_id=p["product_id"],
            isin=p["isin"],
            product_name=p["product_name"],
            currency=p["currency"],
            nominal=p["nominal"],
            distribution_fee_pct=fdata["distribution_fee_pct"],
            structuring_fee_pct=fdata["structuring_fee_pct"],
            management_fee_pct_pa=fdata["management_fee_pct_pa"],
            exchange_fee_pct=fdata["exchange_fee_pct"],
            total_fee_pct=fdata["total_fee_pct"],
            estimated_monetary_amount=fdata["estimated_monetary_amount"],
            description=fdata["description"],
        )
        return Product(
            product_id=p["product_id"],
            isin=p["isin"],
            rfq_id=p["rfq_id"],
            product_name=p["product_name"],
            product_type=p["product_type"],
            basket_type=p["basket_type"],
            status=p["status"],
            currency=p["currency"],
            nominal=p["nominal"],
            client=p["client"],
            created_at=p["created_at"],
            expires_at=p["expires_at"],
            traded_with=p.get("traded_with"),
            traded_price_pct=p.get("traded_price_pct"),
            underlyings=underlying_objs,
            fees=fee_obj,
        )

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

    def get_underlyings(
        self,
        product_id: str | None = None,
        ticker: str | None = None,
        asset_class: str | None = None,
        currency: str | None = None,
        barrier_hit: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Underlying]:
        """Fetch underlying assets across products matching specified filter criteria.

        Args:
            product_id: Filter by product ID, ISIN, or RFQ ID
            ticker: Filter by underlying ticker (e.g. 'NESN SW', 'AAPL US')
            asset_class: Filter by asset class ('Equity', 'Equity Index')
            currency: Filter by underlying currency
            barrier_hit: Filter by whether barrier was breached
            limit: Maximum items to return
            offset: Number of items to skip
        """
        if product_id:
            resolved = self._resolve_product_id(product_id)
            if not resolved or resolved not in self._products:
                return []
            items = [Underlying(**u) for u in self._products[resolved]["underlyings"]]
        else:
            items = self._all_underlyings

        if ticker:
            tick_clean = ticker.strip().upper()
            items = [u for u in items if tick_clean in u.ticker.upper()]

        if asset_class:
            ac_clean = asset_class.strip().lower()
            items = [u for u in items if ac_clean in u.asset_class.lower()]

        if currency:
            curr_clean = currency.strip().upper()
            items = [u for u in items if u.currency.upper() == curr_clean]

        if barrier_hit is not None:
            items = [u for u in items if u.barrier_hit == barrier_hit]

        return items[offset : offset + limit] if limit else items[offset:]

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

    def get_fees(
        self,
        product_id: str | None = None,
        currency: str | None = None,
        max_total_fee_pct: float | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[ProductFeesResponse]:
        """Fetch fee schedules across products matching specified filter criteria.

        Args:
            product_id: Filter by product ID, ISIN, or RFQ ID
            currency: Filter by product currency
            max_total_fee_pct: Filter by maximum total fee percentage
            limit: Maximum items to return
            offset: Number of items to skip
        """
        if product_id:
            resolved = self._resolve_product_id(product_id)
            if not resolved or resolved not in self._products:
                return []
            p_list = [self._products[resolved]]
        else:
            p_list = list(self._products.values())

        if currency:
            curr_clean = currency.strip().upper()
            p_list = [p for p in p_list if p["currency"].upper() == curr_clean]

        if max_total_fee_pct is not None:
            p_list = [p for p in p_list if p["fees"]["total_fee_pct"] <= max_total_fee_pct]

        paginated = p_list[offset : offset + limit] if limit else p_list[offset:]

        res = []
        for pdata in paginated:
            fdata = pdata["fees"]
            nominal = pdata["nominal"]
            curr = pdata["currency"]
            total_fee_pct = fdata["total_fee_pct"]
            monetary_amount = round(nominal * (total_fee_pct / 100.0), 2)
            res.append(
                ProductFeesResponse(
                    product_id=pdata["product_id"],
                    isin=pdata["isin"],
                    product_name=pdata["product_name"],
                    currency=curr,
                    nominal=nominal,
                    distribution_fee_pct=fdata["distribution_fee_pct"],
                    structuring_fee_pct=fdata["structuring_fee_pct"],
                    management_fee_pct_pa=fdata["management_fee_pct_pa"],
                    exchange_fee_pct=fdata["exchange_fee_pct"],
                    total_fee_pct=total_fee_pct,
                    estimated_monetary_amount=monetary_amount,
                    description=fdata["description"],
                )
            )
        return res


sld_service = SLDService()
