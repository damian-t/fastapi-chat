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
    assert len(data) == 10  # default page limit
    assert "productGeneral" in data[0]
    assert "productPricing" in data[0]
    assert "productFees" in data[0]

    # Query with larger limit to get all 100
    res_all = client.get("/api/sld/rfqs?limit=100")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 100

    # Test /products endpoint alias
    res_prods = client.get("/api/sld/products?limit=5")
    assert res_prods.status_code == 200
    assert len(res_prods.json()) == 5

    # Filter status
    res = client.get("/api/sld/rfqs?status=open")
    assert res.status_code == 200
    assert len(res.json()) > 0

    # Filter currency
    res = client.get("/api/sld/rfqs?currency=CHF")
    assert res.status_code == 200
    assert len(res.json()) > 0
    assert all(r["productGeneral"]["currency"] == "CHF" for r in res.json())


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
