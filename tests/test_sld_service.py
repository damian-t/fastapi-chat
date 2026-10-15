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
