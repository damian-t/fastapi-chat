from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_api_sld_rfqs():
    res = client.get("/api/sld/rfqs")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 100
    assert "productGeneral" in data[0]
    assert "productPricing" in data[0]
    assert "productFees" in data[0]

    # Test /products endpoint alias
    res_prods = client.get("/api/sld/products")
    assert res_prods.status_code == 200
    assert len(res_prods.json()) == 100

    # Filter isin
    res = client.get("/api/sld/rfqs?isin=CH1261564201")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["productGeneral"]["isin"] == "CH1261564201"

    # Filter valor
    res = client.get("/api/sld/rfqs?valor=126156101")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["productGeneral"]["valor"] == "126156101"

    # Filter date range
    res = client.get("/api/sld/rfqs?start_date=2026-09-28&end_date=2026-09-29")
    assert res.status_code == 200
    assert len(res.json()) > 0


def test_api_sld_underlyings():
    res = client.get("/api/sld/products/PRD-101/underlyings")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 3
    tickers = [u["underlyingBloombergTicker"] for u in data]
    assert "NESN SW" in tickers

    # Query param endpoint
    res = client.get("/api/sld/underlyings?product_id=RFQ-102")
    assert res.status_code == 200
    data_query = res.json()
    assert isinstance(data_query, list)
    assert len(data_query) == 3


def test_api_sld_fees():
    res = client.get("/api/sld/products/CH1261564201/fees")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 4
    fee_types = [f["feeType"] for f in data]
    assert "distribution" in fee_types
    assert "structuring" in fee_types

    # Query param endpoint
    res = client.get("/api/sld/fees?product_id=RFQ-103")
    assert res.status_code == 200
    data_query = res.json()
    assert isinstance(data_query, list)
    assert len(data_query) == 4


def test_api_sld_not_found():
    res = client.get("/api/sld/products/NONEXISTENT/underlyings")
    assert res.status_code == 404

    res_f = client.get("/api/sld/products/NONEXISTENT/fees")
    assert res_f.status_code == 404
