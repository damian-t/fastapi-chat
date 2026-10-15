import pytest
from app.services.sld_service import sld_service
from app.models.sld import Product, Underlying, Fee


def test_get_rfqs_all():
    rfqs = sld_service.get_rfqs(limit=100)
    assert len(rfqs) == 100
    assert isinstance(rfqs[0], Product)
    assert any(r.productGeneral.productId == 101 for r in rfqs)
    assert any(r.rfq_id == "RFQ-101" for r in rfqs)

    # Default pagination limit is 10
    default_rfqs = sld_service.get_rfqs()
    assert len(default_rfqs) == 10

    # Alias check
    assert sld_service.get_rfq == sld_service.get_rfqs
    assert sld_service.get_products == sld_service.get_rfqs


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
    assert all(r.productGeneral.currency == "USD" for r in usd_rfqs)
    assert all(r.currency == "USD" for r in usd_rfqs)

    chf_rfqs = sld_service.get_rfqs(currency="CHF", limit=50)
    assert len(chf_rfqs) > 0
    assert all(r.productGeneral.currency == "CHF" for r in chf_rfqs)


def test_get_rfqs_filter_issuer():
    zkb_rfqs = sld_service.get_rfqs(issuer="ZKB", limit=50)
    assert len(zkb_rfqs) >= 2


def test_get_rfqs_filter_product_type():
    brc_rfqs = sld_service.get_rfqs(product_type="Barrier Reverse Convertible", limit=50)
    assert len(brc_rfqs) > 0
    assert all("barrier reverse convertible" in r.productGeneral.productType.lower() for r in brc_rfqs)


def test_get_rfqs_filter_client():
    client_rfqs = sld_service.get_rfqs(client="Zurich Cantonal Wealth", limit=50)
    assert len(client_rfqs) > 0
    assert all("zurich cantonal wealth" in r.productGeneral.partyIdentifierClient.lower() for r in client_rfqs)


def test_get_rfqs_by_id():
    rfqs = sld_service.get_rfqs(rfq_id="RFQ-101")
    assert len(rfqs) == 1
    assert rfqs[0].rfq_id == "RFQ-101"
    assert rfqs[0].productGeneral.productId == 101
    assert rfqs[0].productGeneral.isin == "CH1261564201"
    assert len(rfqs[0].productGeneral.underlyingList) == 3


def test_get_underlyings_of_product_success():
    res = sld_service.get_underlyings_of_product("PRD-101")
    assert isinstance(res, list)
    assert len(res) == 3
    assert isinstance(res[0], Underlying)
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "NESN SW" in tickers
    assert "NOVN SW" in tickers
    assert "ROG SW" in tickers


def test_get_underlyings_of_product_via_rfq_id():
    res = sld_service.get_underlyings_of_product("RFQ-101")
    assert isinstance(res, list)
    assert len(res) == 3
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "NESN SW" in tickers


def test_get_underlyings_of_product_via_isin():
    res = sld_service.get_underlyings_of_product("CH1261564202")
    assert isinstance(res, list)
    tickers = [u.underlyingBloombergTicker for u in res]
    assert "AAPL US" in tickers


def test_get_underlyings_of_product_alias():
    res = sld_service.get_underlyings_ofproducts("PRD-101")
    assert isinstance(res, list)
    assert len(res) == 3


def test_get_underlyings_of_product_not_found():
    with pytest.raises(ValueError, match="not found"):
        sld_service.get_underlyings_of_product("UNKNOWN-999")


def test_get_fees_of_product_success():
    fees = sld_service.get_fees_of_product("PRD-101")
    assert isinstance(fees, list)
    assert len(fees) == 4
    assert isinstance(fees[0], Fee)
    dist_fee = next(f for f in fees if f.feeType == "distribution")
    assert dist_fee.amount == 0.5
    assert dist_fee.isPricingRelevant is True


def test_get_fees_of_product_via_rfq():
    fees = sld_service.get_fees_of_product("RFQ-102")
    assert isinstance(fees, list)
    assert len(fees) == 4
    fee_types = [f.feeType for f in fees]
    assert "distribution" in fee_types
    assert "structuring" in fee_types


def test_get_fees_of_product_via_isin():
    fees = sld_service.get_fees_of_product("CH1261564203")
    assert isinstance(fees, list)
    assert len(fees) == 4


def test_get_fees_of_product_not_found():
    with pytest.raises(ValueError, match="not found"):
        sld_service.get_fees_of_product("UNKNOWN-999")
