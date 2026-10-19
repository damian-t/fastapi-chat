import pytest
from datetime import date, datetime, timezone
from app.services.sld_service import sld_service
from app.models.sld import Product, Underlying, Fee


def test_get_rfqs_all():
    rfqs = sld_service.get_rfqs()
    assert len(rfqs) == 100
    assert isinstance(rfqs[0], Product)
    assert any(r.productGeneral.productId == 101 for r in rfqs)
    assert any(r.rfq_id == "RFQ-101" for r in rfqs)

    # Alias check
    assert sld_service.get_rfq == sld_service.get_rfqs
    assert sld_service.get_products == sld_service.get_rfqs


def test_get_rfqs_filter_isin():
    rfqs = sld_service.get_rfqs(isin="CH1261564201")
    assert len(rfqs) == 1
    assert rfqs[0].isin == "CH1261564201"
    assert rfqs[0].productGeneral.productId == 101

    # Case-insensitive
    rfqs_lower = sld_service.get_rfqs(isin="ch1261564201")
    assert len(rfqs_lower) == 1
    assert rfqs_lower[0].productGeneral.productId == 101

    # Non-existent
    assert len(sld_service.get_rfqs(isin="CH9999999999")) == 0


def test_get_rfqs_filter_valor():
    # String valor
    rfqs_str = sld_service.get_rfqs(valor="126156101")
    assert len(rfqs_str) == 1
    assert rfqs_str[0].valor == "126156101"
    assert rfqs_str[0].productGeneral.productId == 101

    # Integer valor
    rfqs_int = sld_service.get_rfqs(valor=126156101)
    assert len(rfqs_int) == 1
    assert rfqs_int[0].productGeneral.productId == 101

    # Non-existent
    assert len(sld_service.get_rfqs(valor=999999999)) == 0


def test_get_rfqs_filter_date_range():
    rfqs = sld_service.get_rfqs(start_date="2026-09-28", end_date="2026-09-29")
    assert len(rfqs) > 0
    start_dt = datetime(2026, 9, 28, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 9, 29, 23, 59, 59, 999999, tzinfo=timezone.utc)
    for r in rfqs:
        created = datetime.fromisoformat(r.productGeneral.initialFixingDate)
        assert start_dt <= created <= end_dt


def test_get_rfqs_filter_start_date_only():
    rfqs = sld_service.get_rfqs(start_date="2026-09-29")
    assert len(rfqs) > 0
    start_dt = datetime(2026, 9, 29, 0, 0, 0, tzinfo=timezone.utc)
    for r in rfqs:
        created = datetime.fromisoformat(r.productGeneral.initialFixingDate)
        assert created >= start_dt


def test_get_rfqs_filter_end_date_only():
    rfqs = sld_service.get_rfqs(end_date="2026-09-20")
    assert len(rfqs) > 0
    end_dt = datetime(2026, 9, 20, 23, 59, 59, 999999, tzinfo=timezone.utc)
    for r in rfqs:
        created = datetime.fromisoformat(r.productGeneral.initialFixingDate)
        assert created <= end_dt


def test_get_rfqs_filter_date_objects():
    rfqs = sld_service.get_rfqs(start_date=date(2026, 9, 28), end_date=date(2026, 9, 29))
    assert len(rfqs) > 0


def test_get_rfqs_combined_filters():
    rfqs = sld_service.get_rfqs(start_date="2026-09-28", isin="CH1261564201")
    assert len(rfqs) == 1
    assert rfqs[0].productGeneral.productId == 101

    # Date out of range with matching isin
    rfqs_out = sld_service.get_rfqs(start_date="2026-09-29", isin="CH1261564201")
    assert len(rfqs_out) == 0


def test_get_rfqs_subset_filters():
    # Currency
    chf_rfqs = sld_service.get_rfqs(currency="CHF")
    assert len(chf_rfqs) > 0
    assert all(r.currency == "CHF" for r in chf_rfqs)

    usd_rfqs = sld_service.get_rfqs(currency="USD")
    assert len(usd_rfqs) > 0
    assert all(r.currency == "USD" for r in usd_rfqs)

    # Status
    open_rfqs = sld_service.get_rfqs(status="open")
    assert len(open_rfqs) > 0
    assert all(r.status == "open" for r in open_rfqs)

    traded_rfqs = sld_service.get_rfqs(status="traded")
    assert len(traded_rfqs) > 0
    assert all(r.status == "traded" for r in traded_rfqs)

    # Issuer
    zkb_rfqs = sld_service.get_rfqs(issuer="ZKB")
    assert len(zkb_rfqs) > 0

    # Product Type
    brc_rfqs = sld_service.get_rfqs(product_type="Barrier Reverse Convertible")
    assert len(brc_rfqs) > 0
    assert all("barrier reverse convertible" in r.product_type.lower() for r in brc_rfqs)

    # Underlying
    nesn_rfqs = sld_service.get_rfqs(underlying="NESN")
    assert len(nesn_rfqs) > 0
    for r in nesn_rfqs:
        tickers = [u.underlyingBloombergTicker for u in r.productGeneral.underlyingList]
        assert any("NESN" in t for t in tickers)


def test_get_rfqs_pagination_limit_and_offset():
    all_rfqs = sld_service.get_rfqs()
    assert len(all_rfqs) == 100

    page_1 = sld_service.get_rfqs(limit=5, offset=0)
    assert len(page_1) == 5
    assert page_1[0].rfq_id == all_rfqs[0].rfq_id

    page_2 = sld_service.get_rfqs(limit=5, offset=5)
    assert len(page_2) == 5
    assert page_2[0].rfq_id == all_rfqs[5].rfq_id
    assert page_1[0].rfq_id != page_2[0].rfq_id

    # Filtered pagination
    open_usd_page = sld_service.get_rfqs(currency="USD", status="open", limit=3, offset=0)
    assert len(open_usd_page) == 3
    assert all(r.currency == "USD" and r.status == "open" for r in open_usd_page)


def test_get_underlyings_for_product_success():
    res = sld_service.get_underlyings_for_product("PRD-101")
    assert isinstance(res, list)
    assert len(res) == 3
    assert isinstance(res[0], Underlying)
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "NESN SW" in tickers
    assert "NOVN SW" in tickers
    assert "ROG SW" in tickers


def test_get_underlyings_for_product_int_id():
    res = sld_service.get_underlyings_for_product(101)
    assert len(res) == 3
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "NESN SW" in tickers


def test_get_underlyings_for_product_via_rfq_id():
    res = sld_service.get_underlyings_for_product("RFQ-101")
    assert len(res) == 3
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "NESN SW" in tickers


def test_get_underlyings_for_product_via_isin():
    res = sld_service.get_underlyings_for_product("CH1261564202")
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "AAPL US" in tickers


def test_get_underlyings_for_product_via_valor():
    res = sld_service.get_underlyings_for_product("126156101")
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "NESN SW" in tickers


def test_get_underlyings_for_product_mandatory():
    with pytest.raises(ValueError, match="mandatory"):
        sld_service.get_underlyings_for_product(None)  # type: ignore

    with pytest.raises(ValueError, match="mandatory"):
        sld_service.get_underlyings_for_product("")

    with pytest.raises(TypeError):
        sld_service.get_underlyings_for_product()  # type: ignore


def test_get_underlyings_for_product_aliases():
    assert sld_service.get_underlyings_of_product == sld_service.get_underlyings_for_product
    assert sld_service.get_underlying_of_product == sld_service.get_underlyings_for_product
    assert sld_service.get_underlyings_ofproducts == sld_service.get_underlyings_for_product


def test_get_underlyings_for_product_not_found():
    with pytest.raises(ValueError, match="not found"):
        sld_service.get_underlyings_for_product("UNKNOWN-999")


def test_get_fees_for_product_success():
    fees = sld_service.get_fees_for_product("PRD-101")
    assert isinstance(fees, list)
    assert len(fees) == 4
    assert isinstance(fees[0], Fee)
    dist_fee = next(f for f in fees if f.feeType == "distribution")
    assert dist_fee.amount == 0.5
    assert dist_fee.isPricingRelevant is True


def test_get_fees_for_product_int_id():
    fees = sld_service.get_fees_for_product(101)
    assert len(fees) == 4


def test_get_fees_for_product_via_rfq():
    fees = sld_service.get_fees_for_product("RFQ-102")
    assert len(fees) == 4
    fee_types = [f.feeType for f in fees]
    assert "distribution" in fee_types
    assert "structuring" in fee_types


def test_get_fees_for_product_via_isin():
    fees = sld_service.get_fees_for_product("CH1261564203")
    assert len(fees) == 4


def test_get_fees_for_product_via_valor():
    fees = sld_service.get_fees_for_product("126156101")
    assert len(fees) == 4


def test_get_fees_for_product_mandatory():
    with pytest.raises(ValueError, match="mandatory"):
        sld_service.get_fees_for_product(None)  # type: ignore

    with pytest.raises(ValueError, match="mandatory"):
        sld_service.get_fees_for_product("")

    with pytest.raises(TypeError):
        sld_service.get_fees_for_product()  # type: ignore


def test_get_fees_for_product_alias():
    assert sld_service.get_fees_of_product == sld_service.get_fees_for_product


def test_get_fees_for_product_not_found():
    with pytest.raises(ValueError, match="not found"):
        sld_service.get_fees_for_product("UNKNOWN-999")


def test_batch_map_reduce_default_batch_size_500():
    result = sld_service.batch_map_reduce_rfqs()
    assert result["batch_size"] == 500
    assert result["total_records_processed"] == 100
    assert result["batches_processed"] == 1
    assert result["total_nominal_volume"] > 0
    assert "CHF" in result["volumes_by_currency"]
    assert "USD" in result["volumes_by_currency"]
    assert "EUR" in result["volumes_by_currency"]
    assert "open" in result["status_distribution"]
    assert result["average_fair_value_pct"] is not None
    assert result["average_entry_costs_pct"] is not None
    assert len(result["top_products_by_volume"]) > 0


def test_batch_map_reduce_chunking_consistency():
    # Run with default batch_size=500
    res_500 = sld_service.batch_map_reduce_rfqs(batch_size=500)

    # Run with small batch_size=15 to force multiple page traversals (100 items -> 7 pages)
    res_15 = sld_service.batch_map_reduce_rfqs(batch_size=15)

    assert res_15["batch_size"] == 15
    assert res_15["batches_processed"] == 7
    assert res_15["total_records_processed"] == res_500["total_records_processed"]
    assert res_15["total_nominal_volume"] == res_500["total_nominal_volume"]
    assert res_15["volumes_by_currency"] == res_500["volumes_by_currency"]
    assert res_15["status_distribution"] == res_500["status_distribution"]
    assert res_15["average_fair_value_pct"] == res_500["average_fair_value_pct"]
    assert res_15["average_entry_costs_pct"] == res_500["average_entry_costs_pct"]


def test_batch_map_reduce_filters():
    res_filtered = sld_service.batch_map_reduce_rfqs(
        filter_params={"status": "open", "currency": "USD"},
        batch_size=500,
    )
    assert res_filtered["total_records_processed"] == 10
    assert set(res_filtered["volumes_by_currency"].keys()) == {"USD"}
    assert res_filtered["status_distribution"] == {"open": 10}


def test_batch_map_reduce_10k_dataset_simulation():
    """Simulate a large dataset of 10,000 RFQs traversed page-by-page with batch_size=500."""
    from unittest.mock import patch

    # Mock get_rfqs to simulate 10,000 products (20 pages of 500)
    orig_prods = sld_service.get_rfqs()
    ten_thousand_prods = [orig_prods[i % len(orig_prods)] for i in range(10000)]

    def mock_paginated_get_rfqs(limit=None, offset=0, **kwargs):
        if limit is None:
            return ten_thousand_prods[offset:]
        return ten_thousand_prods[offset : offset + limit]

    with patch.object(sld_service, "get_rfqs", side_effect=mock_paginated_get_rfqs):
        res = sld_service.batch_map_reduce_rfqs(batch_size=500)
        assert res["batch_size"] == 500
        assert res["batches_processed"] == 20  # Exactly 10,000 / 500 = 20 pages
        assert res["total_records_processed"] == 10000
        assert res["total_nominal_volume"] > 0
        assert res["average_fair_value_pct"] is not None


def test_batch_map_reduce_custom_mapper_reducer():
    def custom_mapper(batch):
        return {
            "batch_count": len(batch),
            "custom_open_count": sum(1 for p in batch if (getattr(p, "_status", None) or getattr(p, "status", None)) == "open"),
        }

    def custom_reducer(accum, batch):
        accum["batch_count"] += batch["batch_count"]
        accum["custom_open_count"] += batch["custom_open_count"]
        return accum

    res = sld_service.batch_map_reduce_rfqs(
        batch_size=20,
        mapper=custom_mapper,
        reducer=custom_reducer,
    )
    assert res["batch_size"] == 20
    assert res["batches_processed"] == 5
    assert res["total_records_processed"] == 100

