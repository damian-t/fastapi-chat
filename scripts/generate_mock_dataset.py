#!/usr/bin/env python3
"""Generate 100 plausible structured product RFQs with underlyings and fees into CSV files."""

import csv
import json
import random
from pathlib import Path

random.seed(42)

SWISS_STOCKS = [
    ("Nestlé SA", "NESN SW", "CHF", 92.50),
    ("Novartis AG", "NOVN SW", "CHF", 99.00),
    ("Roche Holding AG", "ROG SW", "CHF", 248.00),
    ("UBS Group AG", "UBSG SW", "CHF", 27.50),
    ("Zurich Insurance Group AG", "ZURN SW", "CHF", 512.00),
    ("ABB Ltd", "ABBN SW", "CHF", 49.20),
    ("Sika AG", "SIKA SW", "CHF", 262.00),
    ("Geberit AG", "GEBN SW", "CHF", 535.00),
    ("Lonza Group AG", "LONN SW", "CHF", 520.00),
    ("Compagnie Financière Richemont SA", "CFR SW", "CHF", 138.00),
    ("Givaudan SA", "GIVN SW", "CHF", 4150.00),
    ("Swisscom AG", "SCMN SW", "CHF", 545.00),
    ("Alcon AG", "ALC SW", "CHF", 84.00),
    ("Partners Group Holding AG", "PGHN SW", "CHF", 1210.00),
    ("Holcim Ltd", "HOLN SW", "CHF", 82.50),
    ("Swiss Life Holding AG", "SLHN SW", "CHF", 695.00),
    ("Swiss Re AG", "SREN SW", "CHF", 116.00),
    ("Straumann Holding AG", "STMN SW", "CHF", 122.00),
    ("Logitech International SA", "LOGN SW", "CHF", 78.50),
    ("Schindler Holding AG", "SCHN SW", "CHF", 238.00),
]

US_STOCKS = [
    ("Apple Inc.", "AAPL US", "USD", 228.00),
    ("Microsoft Corporation", "MSFT US", "USD", 428.00),
    ("NVIDIA Corporation", "NVDA US", "USD", 122.50),
    ("Amazon.com Inc.", "AMZN US", "USD", 188.00),
    ("Alphabet Inc. Class A", "GOOGL US", "USD", 179.00),
    ("Meta Platforms Inc.", "META US", "USD", 575.00),
    ("Tesla Inc.", "TSLA US", "USD", 218.00),
    ("Broadcom Inc.", "AVGO US", "USD", 172.00),
    ("Advanced Micro Devices Inc.", "AMD US", "USD", 155.00),
    ("JPMorgan Chase & Co.", "JPM US", "USD", 215.00),
    ("Berkshire Hathaway Inc.", "BRK.B US", "USD", 455.00),
    ("Eli Lilly and Company", "LLY US", "USD", 890.00),
    ("Visa Inc.", "V US", "USD", 282.00),
    ("Netflix Inc.", "NFLX US", "USD", 710.00),
    ("Salesforce Inc.", "CRM US", "USD", 270.00),
    ("Qualcomm Inc.", "QCOM US", "USD", 168.00),
]

EU_STOCKS = [
    ("ASML Holding NV", "ASML NA", "EUR", 780.00),
    ("SAP SE", "SAP GY", "EUR", 202.00),
    ("LVMH Moët Hennessy Louis Vuitton", "MC FP", "EUR", 650.00),
    ("Siemens AG", "SIE GY", "EUR", 178.00),
    ("Schneider Electric SE", "SU FP", "EUR", 240.00),
    ("TotalEnergies SE", "TTE FP", "EUR", 61.50),
    ("Sanofi SA", "SAN FP", "EUR", 98.00),
    ("Allianz SE", "ALV GY", "EUR", 285.00),
    ("Air Liquide SA", "AI FP", "EUR", 170.00),
    ("Ferrari NV", "RACE IM", "EUR", 420.00),
    ("Munich Re", "MUV2 GY", "EUR", 480.00),
]

UK_STOCKS = [
    ("AstraZeneca PLC", "AZN LN", "GBP", 120.00),
    ("Shell PLC", "SHEL LN", "GBP", 27.50),
    ("HSBC Holdings PLC", "HSBA LN", "GBP", 6.80),
    ("Unilever PLC", "ULVR LN", "GBP", 48.00),
    ("BP PLC", "BP LN", "GBP", 4.20),
]

INDICES = [
    ("Swiss Market Index", "SMI", "CHF", 12150.00),
    ("Euro Stoxx 50 Index", "SX5E EU", "EUR", 4920.00),
    ("S&P 500 Index", "SPX US", "USD", 5750.00),
    ("Nasdaq 100 Index", "NDX US", "USD", 20100.00),
    ("DAX 40 Index", "DAX GY", "EUR", 19200.00),
    ("FTSE 100 Index", "UKX LN", "GBP", 8280.00),
]

CLIENTS = [
    "Zurich Cantonal Wealth",
    "Geneva Global Alpha",
    "Basel Institutional Funds",
    "Lugano Private Clients",
    "EAM Zurich Partners",
    "St. Gallen Private Wealth",
    "Vaud Family Office",
    "Lucerne Asset Management",
    "Alpen Private Wealth",
    "Helvetia Capital Partners",
    "Lombard Alpine Advisors",
    "Bernese Asset Management",
    "Zug Wealth Management",
    "Rhein Capital Partners",
    "Matterhorn Family Office",
]

ISSUERS = [
    "ZKB",
    "UBS",
    "Vontobel",
    "BNP Paribas",
    "LUKB",
    "Societe Generale",
    "Julius Baer",
    "Goldman Sachs",
    "Morgan Stanley",
    "Barclays",
    "Raiffeisen Switzerland",
]

PRODUCT_TYPES = [
    "Barrier Reverse Convertible",
    "Autocallable BRC",
    "Reverse Convertible",
    "Capital Protection",
    "Express Certificate",
    "Outperformance Certificate",
    "Discount Certificate",
    "Twin-Win Certificate",
]

# Exact first 5 records for backwards compatibility with existing tests
FIRST_5_PRODUCTS = [
    {
        "rfq_id": "RFQ-101",
        "product_id": "PRD-101",
        "isin": "CH1261564201",
        "product_name": "12M Multi Barrier Reverse Convertible on NESN, NOVN, ROG",
        "product_type": "Barrier Reverse Convertible",
        "basket_type": "Worst-of Basket",
        "status": "quoted",
        "currency": "CHF",
        "nominal": 100000.0,
        "client": "Zurich Cantonal Wealth",
        "created_at": "2026-09-28T09:15:00Z",
        "expires_at": "2026-09-28T16:00:00Z",
        "traded_with": None,
        "traded_price_pct": None,
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
    {
        "rfq_id": "RFQ-102",
        "product_id": "PRD-102",
        "isin": "CH1261564202",
        "product_name": "6M Autocallable BRC on AAPL, MSFT, NVDA",
        "product_type": "Autocallable BRC",
        "basket_type": "Worst-of Basket",
        "status": "open",
        "currency": "USD",
        "nominal": 250000.0,
        "client": "Geneva Global Alpha",
        "created_at": "2026-09-29T08:30:00Z",
        "expires_at": "2026-09-29T17:00:00Z",
        "traded_with": None,
        "traded_price_pct": None,
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
    {
        "rfq_id": "RFQ-103",
        "product_id": "PRD-103",
        "isin": "CH1261564203",
        "product_name": "2Y Capital Protection Certificate on Euro Stoxx 50",
        "product_type": "Capital Protection",
        "basket_type": "Single Index Underlying",
        "status": "traded",
        "currency": "EUR",
        "nominal": 500000.0,
        "client": "Basel Institutional Funds",
        "created_at": "2026-09-27T11:00:00Z",
        "expires_at": "2026-09-27T16:00:00Z",
        "traded_with": "ZKB",
        "traded_price_pct": 100.00,
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
    {
        "rfq_id": "RFQ-104",
        "product_id": "PRD-104",
        "isin": "CH1261564204",
        "product_name": "18M Barrier Reverse Convertible on ABB, Sika, Geberit",
        "product_type": "Barrier Reverse Convertible",
        "basket_type": "Worst-of Basket",
        "status": "open",
        "currency": "CHF",
        "nominal": 150000.0,
        "client": "Lugano Private Clients",
        "created_at": "2026-09-29T09:45:00Z",
        "expires_at": "2026-09-29T18:00:00Z",
        "traded_with": None,
        "traded_price_pct": None,
        "quotes": [],
        "best_quote": None,
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
    {
        "rfq_id": "RFQ-105",
        "product_id": "PRD-105",
        "isin": "CH1261564205",
        "product_name": "3M Reverse Convertible on Tesla and Amazon",
        "product_type": "Reverse Convertible",
        "basket_type": "Worst-of Basket",
        "status": "expired",
        "currency": "USD",
        "nominal": 75000.0,
        "client": "EAM Zurich Partners",
        "created_at": "2026-09-25T14:00:00Z",
        "expires_at": "2026-09-25T17:00:00Z",
        "traded_with": None,
        "traded_price_pct": None,
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
]


def generate_plausible_product(index: int) -> dict:
    """Generate product for index 6 to 100 (RFQ-106 to RFQ-200)."""
    rfq_num = 100 + index
    rfq_id = f"RFQ-{rfq_num}"
    product_id = f"PRD-{rfq_num}"
    isin = f"CH1261564{rfq_num:03d}"

    # Pick currency with realistic distribution: 40% CHF, 35% USD, 20% EUR, 5% GBP
    curr_roll = random.random()
    if curr_roll < 0.40:
        currency = "CHF"
        stock_pool = SWISS_STOCKS
    elif curr_roll < 0.75:
        currency = "USD"
        stock_pool = US_STOCKS
    elif curr_roll < 0.95:
        currency = "EUR"
        stock_pool = EU_STOCKS
    else:
        currency = "GBP"
        stock_pool = UK_STOCKS

    # Product structure type
    ptype = random.choice(PRODUCT_TYPES)

    # Tenors
    tenor = random.choice(["3M", "6M", "9M", "12M", "18M", "24M", "3Y"])

    # Determine underlyings
    underlyings = []
    if ptype == "Capital Protection" and random.random() < 0.6:
        # Index underlying
        matching_indices = [idx for idx in INDICES if idx[2] == currency]
        idx_choice = random.choice(matching_indices) if matching_indices else INDICES[0]
        basket_type = "Single Index Underlying"
        spot = idx_choice[3]
        perf = round(random.uniform(-8.0, 15.0), 2)
        curr_price = round(spot * (1 + perf / 100.0), 2)
        underlyings.append({
            "name": idx_choice[0],
            "ticker": idx_choice[1],
            "asset_class": "Equity Index",
            "currency": idx_choice[2],
            "spot_price": spot,
            "strike_level_pct": 100.0,
            "barrier_level_pct": None,
            "current_price": curr_price,
            "performance_pct": perf,
            "barrier_hit": False,
            "distance_to_barrier_pct": None,
        })
        product_name = f"{tenor} Capital Protection Certificate on {idx_choice[1]}"
    else:
        # Stock basket
        num_stocks = random.choice([1, 2, 3, 3, 4])
        selected_stocks = random.sample(stock_pool, min(num_stocks, len(stock_pool)))
        basket_type = "Worst-of Basket" if len(selected_stocks) > 1 else "Single Underlying"

        has_barrier = ptype not in ["Capital Protection"]
        default_barrier = random.choice([55.0, 60.0, 65.0, 70.0, 75.0]) if has_barrier else None

        for name, ticker, curr, spot in selected_stocks:
            # Plausible price movement between -30% and +25%
            perf = round(random.uniform(-25.0, 20.0), 2)
            curr_price = round(spot * (1 + perf / 100.0), 2)

            barrier_hit = False
            dist_to_barrier = None
            if default_barrier is not None:
                current_pct = (curr_price / spot) * 100.0
                dist_to_barrier = round(current_pct - default_barrier, 2)
                barrier_hit = dist_to_barrier <= 0

            underlyings.append({
                "name": name,
                "ticker": ticker,
                "asset_class": "Equity",
                "currency": curr,
                "spot_price": spot,
                "strike_level_pct": 100.0,
                "barrier_level_pct": default_barrier,
                "current_price": curr_price,
                "performance_pct": perf,
                "barrier_hit": barrier_hit,
                "distance_to_barrier_pct": dist_to_barrier,
            })

        tickers_str = ", ".join(u["ticker"].split()[0] for u in underlyings)
        prefix = f"{tenor} {ptype}"
        if len(underlyings) > 1 and "Multi" not in prefix and "Basket" not in prefix:
            prefix = f"{tenor} Multi {ptype}"
        product_name = f"{prefix} on {tickers_str}"

    # Status: realistic lifecycle distribution
    status_roll = random.random()
    if status_roll < 0.25:
        status = "open"
    elif status_roll < 0.65:
        status = "quoted"
    elif status_roll < 0.88:
        status = "traded"
    elif status_roll < 0.95:
        status = "expired"
    else:
        status = "rejected"

    nominal_choices = [50000.0, 100000.0, 150000.0, 200000.0, 250000.0, 500000.0, 1000000.0]
    nominal = float(random.choice(nominal_choices))
    client = random.choice(CLIENTS)

    # Dates
    day = random.randint(15, 30)
    created_at = f"2026-09-{day:02d}T09:{random.randint(10, 50):02d}:00Z"
    expires_at = f"2026-09-{day:02d}T17:00:00Z"

    # Quotes
    quotes = []
    best_quote = None
    traded_with = None
    traded_price_pct = None

    if status in ["quoted", "traded", "expired"]:
        num_quotes = random.randint(1, 4)
        quote_issuers = random.sample(ISSUERS, num_quotes)
        base_coupon = round(random.uniform(4.5, 12.5), 2)
        for q_iss in quote_issuers:
            coupon = round(base_coupon + random.uniform(-0.5, 0.5), 2)
            price = round(random.uniform(99.4, 100.3), 2)
            q_time = f"2026-09-{day:02d}T10:{random.randint(10, 55):02d}:00Z"
            quotes.append({
                "issuer": q_iss,
                "price_pct": price,
                "coupon_pct_pa": coupon,
                "timestamp": q_time,
                "valid_until": expires_at,
            })
        # Best quote is highest coupon or best price
        best_quote = max(quotes, key=lambda q: (q["coupon_pct_pa"], -q["price_pct"]))

        if status == "traded":
            winner = best_quote or random.choice(quotes)
            traded_with = winner["issuer"]
            traded_price_pct = winner["price_pct"]
    elif status == "open" and random.random() < 0.4:
        # Awaiting more quotes, maybe 1 quote already in
        q_iss = random.choice(ISSUERS)
        price = round(random.uniform(99.5, 100.2), 2)
        coupon = round(random.uniform(5.0, 11.0), 2)
        q = {
            "issuer": q_iss,
            "price_pct": price,
            "coupon_pct_pa": coupon,
            "timestamp": f"2026-09-{day:02d}T10:15:00Z",
            "valid_until": expires_at,
        }
        quotes.append(q)
        best_quote = q

    # Fees
    dist_fee = round(random.choice([0.25, 0.30, 0.40, 0.50, 0.60, 0.75]), 2)
    struct_fee = round(random.choice([0.15, 0.20, 0.25, 0.30]), 2)
    mgmt_fee = round(random.choice([0.0, 0.0, 0.05, 0.10, 0.15]), 2)
    exch_fee = round(random.choice([0.02, 0.03, 0.05]), 2)
    total_fee = round(dist_fee + struct_fee + mgmt_fee + exch_fee, 2)

    fee_desc = (
        f"{tenor} {ptype} fee schedule: {int(dist_fee*100)} bps distribution, "
        f"{int(struct_fee*100)} bps structuring"
    )
    if mgmt_fee > 0:
        fee_desc += f", {int(mgmt_fee*100)} bps p.a. management fee"
    fee_desc += f", {int(exch_fee*100)} bps exchange clearing."

    fees = {
        "distribution_fee_pct": dist_fee,
        "structuring_fee_pct": struct_fee,
        "management_fee_pct_pa": mgmt_fee,
        "exchange_fee_pct": exch_fee,
        "total_fee_pct": total_fee,
        "description": fee_desc,
    }

    return {
        "rfq_id": rfq_id,
        "product_id": product_id,
        "isin": isin,
        "product_name": product_name,
        "product_type": ptype,
        "basket_type": basket_type,
        "status": status,
        "currency": currency,
        "nominal": nominal,
        "client": client,
        "created_at": created_at,
        "expires_at": expires_at,
        "traded_with": traded_with,
        "traded_price_pct": traded_price_pct,
        "quotes": quotes,
        "best_quote": best_quote,
        "underlyings": underlyings,
        "fees": fees,
    }


def generate_all_100_products() -> list[dict]:
    products = list(FIRST_5_PRODUCTS)
    for i in range(6, 101):
        products.append(generate_plausible_product(i))
    return products


def save_to_csv(products: list[dict], data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    master_csv_path = data_dir / "rfq_products.csv"
    underlyings_csv_path = data_dir / "underlyings.csv"
    fees_csv_path = data_dir / "fees.csv"

    # 1. Master CSV containing all attributes
    master_headers = [
        "rfq_id",
        "product_id",
        "isin",
        "product_name",
        "product_type",
        "basket_type",
        "status",
        "currency",
        "nominal",
        "client",
        "created_at",
        "expires_at",
        "traded_with",
        "traded_price_pct",
        "quotes",
        "best_quote",
        "underlying_tickers",
        "underlyings",
        "distribution_fee_pct",
        "structuring_fee_pct",
        "management_fee_pct_pa",
        "exchange_fee_pct",
        "total_fee_pct",
        "fee_description",
    ]

    with open(master_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=master_headers)
        writer.writeheader()
        for p in products:
            tickers = "; ".join(u["ticker"] for u in p["underlyings"])
            fees = p["fees"]
            writer.writerow({
                "rfq_id": p["rfq_id"],
                "product_id": p["product_id"],
                "isin": p["isin"],
                "product_name": p["product_name"],
                "product_type": p["product_type"],
                "basket_type": p["basket_type"],
                "status": p["status"],
                "currency": p["currency"],
                "nominal": p["nominal"],
                "client": p["client"],
                "created_at": p["created_at"],
                "expires_at": p["expires_at"],
                "traded_with": p["traded_with"] or "",
                "traded_price_pct": p["traded_price_pct"] if p["traded_price_pct"] is not None else "",
                "quotes": json.dumps(p["quotes"]),
                "best_quote": json.dumps(p["best_quote"]) if p["best_quote"] else "",
                "underlying_tickers": tickers,
                "underlyings": json.dumps(p["underlyings"]),
                "distribution_fee_pct": fees["distribution_fee_pct"],
                "structuring_fee_pct": fees["structuring_fee_pct"],
                "management_fee_pct_pa": fees["management_fee_pct_pa"],
                "exchange_fee_pct": fees["exchange_fee_pct"],
                "total_fee_pct": fees["total_fee_pct"],
                "fee_description": fees["description"],
            })

    # 2. Normalized Underlyings CSV
    underlyings_headers = [
        "product_id",
        "isin",
        "rfq_id",
        "name",
        "ticker",
        "asset_class",
        "currency",
        "spot_price",
        "strike_level_pct",
        "barrier_level_pct",
        "current_price",
        "performance_pct",
        "barrier_hit",
        "distance_to_barrier_pct",
    ]
    with open(underlyings_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=underlyings_headers)
        writer.writeheader()
        for p in products:
            for u in p["underlyings"]:
                writer.writerow({
                    "product_id": p["product_id"],
                    "isin": p["isin"],
                    "rfq_id": p["rfq_id"],
                    "name": u["name"],
                    "ticker": u["ticker"],
                    "asset_class": u["asset_class"],
                    "currency": u["currency"],
                    "spot_price": u["spot_price"],
                    "strike_level_pct": u["strike_level_pct"],
                    "barrier_level_pct": u["barrier_level_pct"] if u["barrier_level_pct"] is not None else "",
                    "current_price": u["current_price"],
                    "performance_pct": u["performance_pct"],
                    "barrier_hit": u["barrier_hit"],
                    "distance_to_barrier_pct": u["distance_to_barrier_pct"] if u["distance_to_barrier_pct"] is not None else "",
                })

    # 3. Normalized Fees CSV
    fees_headers = [
        "product_id",
        "isin",
        "rfq_id",
        "product_name",
        "currency",
        "nominal",
        "distribution_fee_pct",
        "structuring_fee_pct",
        "management_fee_pct_pa",
        "exchange_fee_pct",
        "total_fee_pct",
        "estimated_monetary_amount",
        "description",
    ]
    with open(fees_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fees_headers)
        writer.writeheader()
        for p in products:
            fees = p["fees"]
            nominal = p["nominal"]
            total_fee = fees["total_fee_pct"]
            writer.writerow({
                "product_id": p["product_id"],
                "isin": p["isin"],
                "rfq_id": p["rfq_id"],
                "product_name": p["product_name"],
                "currency": p["currency"],
                "nominal": nominal,
                "distribution_fee_pct": fees["distribution_fee_pct"],
                "structuring_fee_pct": fees["structuring_fee_pct"],
                "management_fee_pct_pa": fees["management_fee_pct_pa"],
                "exchange_fee_pct": fees["exchange_fee_pct"],
                "total_fee_pct": total_fee,
                "estimated_monetary_amount": round(nominal * (total_fee / 100.0), 2),
                "description": fees["description"],
            })


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "app" / "data"
    products = generate_all_100_products()
    save_to_csv(products, data_dir)
    print(f"Successfully generated {len(products)} RFQ products into {data_dir}")
