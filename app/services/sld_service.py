from typing import Any
from app.models.sld import (
    RFQ,
    RFQQuote,
    Underlying,
    ProductUnderlyingsResponse,
    ProductFeesResponse,
)


class SLDService:
    """Mock SLD Service providing data for structured product RFQs, underlyings, and fees."""

    def __init__(self) -> None:
        self._rfqs: list[dict[str, Any]] = [
            {
                "rfq_id": "RFQ-101",
                "product_id": "PRD-101",
                "isin": "CH1261564201",
                "product_name": "12M Multi Barrier Reverse Convertible on NESN, NOVN, ROG",
                "product_type": "Barrier Reverse Convertible",
                "status": "quoted",
                "currency": "CHF",
                "nominal": 100000.0,
                "client": "Zurich Cantonal Wealth",
                "underlyings": ["NESN SW", "NOVN SW", "ROG SW"],
                "quotes": [
                    {
                        "issuer": "ZKB",
                        "price_pct": 99.85,
                        "coupon_pct_pa": 7.20,
                        "timestamp": "2026-09-28T09:20:00Z",
                        "valid_until": "2026-09-28T16:00:00Z",
                    },
                    {
                        "issuer": "UBS",
                        "price_pct": 99.70,
                        "coupon_pct_pa": 7.10,
                        "timestamp": "2026-09-28T09:22:00Z",
                        "valid_until": "2026-09-28T16:00:00Z",
                    },
                    {
                        "issuer": "Vontobel",
                        "price_pct": 100.10,
                        "coupon_pct_pa": 7.25,
                        "timestamp": "2026-09-28T09:25:00Z",
                        "valid_until": "2026-09-28T16:00:00Z",
                    },
                ],
                "best_quote": {
                    "issuer": "Vontobel",
                    "price_pct": 100.10,
                    "coupon_pct_pa": 7.25,
                    "timestamp": "2026-09-28T09:25:00Z",
                    "valid_until": "2026-09-28T16:00:00Z",
                },
                "traded_with": None,
                "traded_price_pct": None,
                "created_at": "2026-09-28T09:15:00Z",
                "expires_at": "2026-09-28T16:00:00Z",
            },
            {
                "rfq_id": "RFQ-102",
                "product_id": "PRD-102",
                "isin": "CH1261564202",
                "product_name": "6M Autocallable BRC on AAPL, MSFT, NVDA",
                "product_type": "Autocallable BRC",
                "status": "open",
                "currency": "USD",
                "nominal": 250000.0,
                "client": "Geneva Global Alpha",
                "underlyings": ["AAPL US", "MSFT US", "NVDA US"],
                "quotes": [
                    {
                        "issuer": "BNP Paribas",
                        "price_pct": 99.90,
                        "coupon_pct_pa": 9.50,
                        "timestamp": "2026-09-29T08:45:00Z",
                        "valid_until": "2026-09-29T17:00:00Z",
                    }
                ],
                "best_quote": {
                    "issuer": "BNP Paribas",
                    "price_pct": 99.90,
                    "coupon_pct_pa": 9.50,
                    "timestamp": "2026-09-29T08:45:00Z",
                    "valid_until": "2026-09-29T17:00:00Z",
                },
                "traded_with": None,
                "traded_price_pct": None,
                "created_at": "2026-09-29T08:30:00Z",
                "expires_at": "2026-09-29T17:00:00Z",
            },
            {
                "rfq_id": "RFQ-103",
                "product_id": "PRD-103",
                "isin": "CH1261564203",
                "product_name": "2Y Capital Protection Certificate on Euro Stoxx 50",
                "product_type": "Capital Protection",
                "status": "traded",
                "currency": "EUR",
                "nominal": 500000.0,
                "client": "Basel Institutional Funds",
                "underlyings": ["SX5E EU"],
                "quotes": [
                    {
                        "issuer": "ZKB",
                        "price_pct": 100.00,
                        "coupon_pct_pa": 3.50,
                        "timestamp": "2026-09-27T11:15:00Z",
                        "valid_until": "2026-09-27T16:00:00Z",
                    },
                    {
                        "issuer": "UBS",
                        "price_pct": 99.80,
                        "coupon_pct_pa": 3.25,
                        "timestamp": "2026-09-27T11:20:00Z",
                        "valid_until": "2026-09-27T16:00:00Z",
                    },
                ],
                "best_quote": {
                    "issuer": "ZKB",
                    "price_pct": 100.00,
                    "coupon_pct_pa": 3.50,
                    "timestamp": "2026-09-27T11:15:00Z",
                    "valid_until": "2026-09-27T16:00:00Z",
                },
                "traded_with": "ZKB",
                "traded_price_pct": 100.00,
                "created_at": "2026-09-27T11:00:00Z",
                "expires_at": "2026-09-27T16:00:00Z",
            },
            {
                "rfq_id": "RFQ-104",
                "product_id": "PRD-104",
                "isin": "CH1261564204",
                "product_name": "18M Barrier Reverse Convertible on ABB, Sika, Geberit",
                "product_type": "Barrier Reverse Convertible",
                "status": "open",
                "currency": "CHF",
                "nominal": 150000.0,
                "client": "Lugano Private Clients",
                "underlyings": ["ABBN SW", "SIKA SW", "GEBN SW"],
                "quotes": [],
                "best_quote": None,
                "traded_with": None,
                "traded_price_pct": None,
                "created_at": "2026-09-29T09:45:00Z",
                "expires_at": "2026-09-29T18:00:00Z",
            },
            {
                "rfq_id": "RFQ-105",
                "product_id": "PRD-105",
                "isin": "CH1261564205",
                "product_name": "3M Reverse Convertible on Tesla and Amazon",
                "product_type": "Reverse Convertible",
                "status": "expired",
                "currency": "USD",
                "nominal": 75000.0,
                "client": "EAM Zurich Partners",
                "underlyings": ["TSLA US", "AMZN US"],
                "quotes": [
                    {
                        "issuer": "UBS",
                        "price_pct": 99.50,
                        "coupon_pct_pa": 8.80,
                        "timestamp": "2026-09-25T14:30:00Z",
                        "valid_until": "2026-09-25T17:00:00Z",
                    }
                ],
                "best_quote": {
                    "issuer": "UBS",
                    "price_pct": 99.50,
                    "coupon_pct_pa": 8.80,
                    "timestamp": "2026-09-25T14:30:00Z",
                    "valid_until": "2026-09-25T17:00:00Z",
                },
                "traded_with": None,
                "traded_price_pct": None,
                "created_at": "2026-09-25T14:00:00Z",
                "expires_at": "2026-09-25T17:00:00Z",
            },
        ]

        self._products: dict[str, dict[str, Any]] = {
            "PRD-101": {
                "isin": "CH1261564201",
                "product_name": "12M Multi Barrier Reverse Convertible on NESN, NOVN, ROG",
                "basket_type": "Worst-of Basket",
                "currency": "CHF",
                "nominal": 100000.0,
                "underlyings": [
                    {
                        "name": "Nestlé SA",
                        "ticker": "NESN SW",
                        "asset_class": "Equity",
                        "currency": "CHF",
                        "spot_price": 94.20,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 65.0,
                        "current_price": 93.50,
                        "performance_pct": -0.74,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 34.20,
                    },
                    {
                        "name": "Novartis AG",
                        "ticker": "NOVN SW",
                        "asset_class": "Equity",
                        "currency": "CHF",
                        "spot_price": 98.40,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 65.0,
                        "current_price": 101.20,
                        "performance_pct": 2.85,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 37.85,
                    },
                    {
                        "name": "Roche Holding AG",
                        "ticker": "ROG SW",
                        "asset_class": "Equity",
                        "currency": "CHF",
                        "spot_price": 245.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 65.0,
                        "current_price": 242.10,
                        "performance_pct": -1.18,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 33.82,
                    },
                ],
                "fees": {
                    "distribution_fee_pct": 0.50,
                    "structuring_fee_pct": 0.25,
                    "management_fee_pct_pa": 0.00,
                    "exchange_fee_pct": 0.05,
                    "total_fee_pct": 0.80,
                    "description": "Standard BRC fee model: 50 bps distribution fee, 25 bps structuring fee, 5 bps exchange clearing fee.",
                },
            },
            "PRD-102": {
                "isin": "CH1261564202",
                "product_name": "6M Autocallable BRC on AAPL, MSFT, NVDA",
                "basket_type": "Worst-of Basket",
                "currency": "USD",
                "nominal": 250000.0,
                "underlyings": [
                    {
                        "name": "Apple Inc.",
                        "ticker": "AAPL US",
                        "asset_class": "Equity",
                        "currency": "USD",
                        "spot_price": 225.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 70.0,
                        "current_price": 228.50,
                        "performance_pct": 1.56,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 31.56,
                    },
                    {
                        "name": "Microsoft Corporation",
                        "ticker": "MSFT US",
                        "asset_class": "Equity",
                        "currency": "USD",
                        "spot_price": 430.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 70.0,
                        "current_price": 425.00,
                        "performance_pct": -1.16,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 28.84,
                    },
                    {
                        "name": "NVIDIA Corporation",
                        "ticker": "NVDA US",
                        "asset_class": "Equity",
                        "currency": "USD",
                        "spot_price": 120.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 70.0,
                        "current_price": 124.80,
                        "performance_pct": 4.00,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 34.00,
                    },
                ],
                "fees": {
                    "distribution_fee_pct": 0.40,
                    "structuring_fee_pct": 0.20,
                    "management_fee_pct_pa": 0.10,
                    "exchange_fee_pct": 0.05,
                    "total_fee_pct": 0.75,
                    "description": "Autocallable US Tech fee schedule: 40 bps distribution fee, 20 bps structuring fee, 10 bps annual management fee.",
                },
            },
            "PRD-103": {
                "isin": "CH1261564203",
                "product_name": "2Y Capital Protection Certificate on Euro Stoxx 50",
                "basket_type": "Single Index Underlying",
                "currency": "EUR",
                "nominal": 500000.0,
                "underlyings": [
                    {
                        "name": "Euro Stoxx 50 Index",
                        "ticker": "SX5E EU",
                        "asset_class": "Equity Index",
                        "currency": "EUR",
                        "spot_price": 4900.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": None,
                        "current_price": 4950.00,
                        "performance_pct": 1.02,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": None,
                    }
                ],
                "fees": {
                    "distribution_fee_pct": 0.30,
                    "structuring_fee_pct": 0.15,
                    "management_fee_pct_pa": 0.05,
                    "exchange_fee_pct": 0.02,
                    "total_fee_pct": 0.52,
                    "description": "Capital protection structure with institutional scale: 30 bps distribution, 15 bps structuring, 5 bps mgmt fee.",
                },
            },
            "PRD-104": {
                "isin": "CH1261564204",
                "product_name": "18M Barrier Reverse Convertible on ABB, Sika, Geberit",
                "basket_type": "Worst-of Basket",
                "currency": "CHF",
                "nominal": 150000.0,
                "underlyings": [
                    {
                        "name": "ABB Ltd",
                        "ticker": "ABBN SW",
                        "asset_class": "Equity",
                        "currency": "CHF",
                        "spot_price": 48.50,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 60.0,
                        "current_price": 47.90,
                        "performance_pct": -1.24,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 38.76,
                    },
                    {
                        "name": "Sika AG",
                        "ticker": "SIKA SW",
                        "asset_class": "Equity",
                        "currency": "CHF",
                        "spot_price": 265.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 60.0,
                        "current_price": 270.20,
                        "performance_pct": 1.96,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 41.96,
                    },
                    {
                        "name": "Geberit AG",
                        "ticker": "GEBN SW",
                        "asset_class": "Equity",
                        "currency": "CHF",
                        "spot_price": 540.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 60.0,
                        "current_price": 538.00,
                        "performance_pct": -0.37,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 39.63,
                    },
                ],
                "fees": {
                    "distribution_fee_pct": 0.60,
                    "structuring_fee_pct": 0.30,
                    "management_fee_pct_pa": 0.00,
                    "exchange_fee_pct": 0.05,
                    "total_fee_pct": 0.95,
                    "description": "18M Swiss industrial basket: 60 bps distribution, 30 bps structuring fee.",
                },
            },
            "PRD-105": {
                "isin": "CH1261564205",
                "product_name": "3M Reverse Convertible on Tesla and Amazon",
                "basket_type": "Worst-of Basket",
                "currency": "USD",
                "nominal": 75000.0,
                "underlyings": [
                    {
                        "name": "Tesla Inc.",
                        "ticker": "TSLA US",
                        "asset_class": "Equity",
                        "currency": "USD",
                        "spot_price": 215.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 75.0,
                        "current_price": 202.00,
                        "performance_pct": -6.05,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 18.95,
                    },
                    {
                        "name": "Amazon.com Inc.",
                        "ticker": "AMZN US",
                        "asset_class": "Equity",
                        "currency": "USD",
                        "spot_price": 185.00,
                        "strike_level_pct": 100.0,
                        "barrier_level_pct": 75.0,
                        "current_price": 189.50,
                        "performance_pct": 2.43,
                        "barrier_hit": False,
                        "distance_to_barrier_pct": 27.43,
                    },
                ],
                "fees": {
                    "distribution_fee_pct": 0.50,
                    "structuring_fee_pct": 0.25,
                    "management_fee_pct_pa": 0.00,
                    "exchange_fee_pct": 0.05,
                    "total_fee_pct": 0.80,
                    "description": "Short-tenor US dual-equity RC: 50 bps distribution fee, 25 bps structuring fee.",
                },
            },
        }

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
        limit: int = 10,
    ) -> list[RFQ]:
        """Fetch RFQs matching specified filters.

        Args:
            rfq_id: Filter by exact or partial RFQ ID (e.g. 'RFQ-101')
            status: Filter by status ('open', 'quoted', 'traded', 'expired', 'rejected')
            issuer: Filter by quoted or traded issuer (e.g. 'ZKB', 'UBS', 'Vontobel', 'BNP Paribas')
            product_type: Filter by product structure type
            currency: Filter by currency (e.g. 'CHF', 'USD', 'EUR')
            limit: Maximum number of RFQs to return
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

        return [RFQ(**r) for r in results[:limit]]

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
