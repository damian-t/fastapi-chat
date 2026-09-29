import pytest
from app.services.sld_service import sld_service


def test_get_rfqs_all():
    rfqs = sld_service.get_rfqs()
    assert len(rfqs) == 5
    assert any(r.rfq_id == "RFQ-101" for r in rfqs)


def test_get_rfqs_filter_status():
    open_rfqs = sld_service.get_rfqs(status="open")
    assert len(open_rfqs) == 2
    assert all(r.status == "open" for r in open_rfqs)

    traded_rfqs = sld_service.get_rfqs(status="traded")
    assert len(traded_rfqs) == 1
    assert traded_rfqs[0].rfq_id == "RFQ-103"


def test_get_rfqs_filter_currency():
    usd_rfqs = sld_service.get_rfqs(currency="USD")
    assert len(usd_rfqs) == 2
    assert all(r.currency == "USD" for r in usd_rfqs)


def test_get_rfqs_filter_issuer():
    zkb_rfqs = sld_service.get_rfqs(issuer="ZKB")
    assert len(zkb_rfqs) >= 2


def test_get_rfqs_by_id():
    rfqs = sld_service.get_rfqs(rfq_id="RFQ-101")
    assert len(rfqs) == 1
    assert rfqs[0].rfq_id == "RFQ-101"
    assert rfqs[0].best_quote.issuer == "Vontobel"


def test_get_underlyings_of_product_success():
    res = sld_service.get_underlyings_of_product("PRD-101")
    assert res.product_id == "PRD-101"
    assert res.isin == "CH1261564201"
    assert len(res.underlyings) == 3
    tickers = [u.ticker for u in res.underlyings]
    assert "NESN SW" in tickers


def test_get_underlyings_of_product_via_rfq_id():
    res = sld_service.get_underlyings_of_product("RFQ-101")
    assert res.isin == "CH1261564201"
    assert len(res.underlyings) == 3


def test_get_underlyings_of_product_via_isin():
    res = sld_service.get_underlyings_of_product("CH1261564202")
    assert res.product_id == "PRD-102"
    tickers = [u.ticker for u in res.underlyings]
    assert "AAPL US" in tickers


def test_get_underlyings_of_product_not_found():
    with pytest.raises(ValueError, match="not found"):
        sld_service.get_underlyings_of_product("UNKNOWN-999")


def test_get_fees_of_product_success():
    fees = sld_service.get_fees_of_product("PRD-101")
    assert fees.isin == "CH1261564201"
    assert fees.total_fee_pct == 0.80
    assert fees.estimated_monetary_amount == 800.0


def test_get_fees_of_product_via_rfq():
    fees = sld_service.get_fees_of_product("RFQ-102")
    assert fees.currency == "USD"
    assert fees.total_fee_pct == 0.75
    assert fees.estimated_monetary_amount == 1875.0
