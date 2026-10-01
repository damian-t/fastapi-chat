import pytest
from app.services.sld_service import sld_service


def test_get_rfqs_all():
    rfqs = sld_service.get_rfqs(limit=100)
    assert len(rfqs) == 100
    assert any(r.rfq_id == "RFQ-101" for r in rfqs)
    assert any(r.rfq_id == "RFQ-200" for r in rfqs)

    # Default pagination limit is 10
    default_rfqs = sld_service.get_rfqs()
    assert len(default_rfqs) == 10


def test_get_rfqs_filter_status():
    open_rfqs = sld_service.get_rfqs(status="open", limit=50)
    assert len(open_rfqs) > 0
    assert all(r.status == "open" for r in open_rfqs)

    traded_rfqs = sld_service.get_rfqs(status="traded", limit=50)
    assert len(traded_rfqs) > 0
    assert all(r.status == "traded" for r in traded_rfqs)
    assert any(r.rfq_id == "RFQ-103" for r in traded_rfqs)


def test_get_rfqs_filter_currency():
    usd_rfqs = sld_service.get_rfqs(currency="USD", limit=50)
    assert len(usd_rfqs) > 0
    assert all(r.currency == "USD" for r in usd_rfqs)

    chf_rfqs = sld_service.get_rfqs(currency="CHF", limit=50)
    assert len(chf_rfqs) > 0
    assert all(r.currency == "CHF" for r in chf_rfqs)


def test_get_rfqs_filter_issuer():
    zkb_rfqs = sld_service.get_rfqs(issuer="ZKB", limit=50)
    assert len(zkb_rfqs) >= 2


def test_get_rfqs_by_id():
    rfqs = sld_service.get_rfqs(rfq_id="RFQ-101")
    assert len(rfqs) == 1
    assert rfqs[0].rfq_id == "RFQ-101"
    assert rfqs[0].best_quote.issuer == "Vontobel"


def test_get_products_all():
    products = sld_service.get_products(limit=100)
    assert len(products) == 100
    assert products[0].product_id == "PRD-101"
    assert products[-1].product_id == "PRD-200"


def test_get_products_filter_product_type():
    brc_products = sld_service.get_products(product_type="Barrier Reverse Convertible", limit=50)
    assert len(brc_products) > 0
    assert all("barrier reverse convertible" in p.product_type.lower() for p in brc_products)


def test_get_products_filter_currency():
    chf_products = sld_service.get_products(currency="CHF", limit=50)
    assert len(chf_products) > 0
    assert all(p.currency == "CHF" for p in chf_products)


def test_get_products_filter_client():
    client_products = sld_service.get_products(client="Zurich Cantonal Wealth", limit=50)
    assert len(client_products) > 0
    assert all("zurich cantonal wealth" in p.client.lower() for p in client_products)


def test_get_product_by_id():
    p = sld_service.get_product_by_id("PRD-101")
    assert p.product_id == "PRD-101"
    assert p.isin == "CH1261564201"
    assert len(p.underlyings) == 3
    assert p.fees is not None
    assert p.fees.total_fee_pct == 0.80


def test_get_product_by_id_via_isin_or_rfq():
    p_isin = sld_service.get_product_by_id("CH1261564202")
    assert p_isin.product_id == "PRD-102"

    p_rfq = sld_service.get_product_by_id("RFQ-103")
    assert p_rfq.product_id == "PRD-103"


def test_get_product_by_id_not_found():
    with pytest.raises(ValueError, match="not found"):
        sld_service.get_product_by_id("NONEXISTENT-999")


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


def test_get_underlyings_filter_criteria():
    nesn = sld_service.get_underlyings(ticker="NESN SW")
    assert len(nesn) > 0
    assert all("NESN SW" in u.ticker for u in nesn)

    indices = sld_service.get_underlyings(asset_class="Equity Index")
    assert len(indices) > 0
    assert all(u.asset_class.lower() == "equity index" for u in indices)

    breached = sld_service.get_underlyings(barrier_hit=True)
    assert all(u.barrier_hit is True for u in breached)


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


def test_get_fees_filter_criteria():
    low_fee = sld_service.get_fees(max_total_fee_pct=0.60, limit=50)
    assert len(low_fee) > 0
    assert all(f.total_fee_pct <= 0.60 for f in low_fee)

    chf_fees = sld_service.get_fees(currency="CHF", limit=50)
    assert len(chf_fees) > 0
    assert all(f.currency == "CHF" for f in chf_fees)
