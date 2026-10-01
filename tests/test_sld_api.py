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

    # Query with larger limit to get all 100
    res_all = client.get("/api/sld/rfqs?limit=100")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 100

    # Filter status
    res = client.get("/api/sld/rfqs?status=open")
    assert res.status_code == 200
    assert len(res.json()) > 0
    assert all(r["status"] == "open" for r in res.json())

    # Filter currency
    res = client.get("/api/sld/rfqs?currency=CHF")
    assert res.status_code == 200
    assert len(res.json()) > 0
    assert all(r["currency"] == "CHF" for r in res.json())


def test_api_sld_products():
    res = client.get("/api/sld/products?limit=100")
    assert res.status_code == 200
    products = res.json()
    assert len(products) == 100
    assert products[0]["product_id"] == "PRD-101"

    # Filter by currency
    res_usd = client.get("/api/sld/products?currency=USD")
    assert res_usd.status_code == 200
    assert all(p["currency"] == "USD" for p in res_usd.json())

    # Single product by ID
    res_single = client.get("/api/sld/products/PRD-101")
    assert res_single.status_code == 200
    assert res_single.json()["isin"] == "CH1261564201"
    assert len(res_single.json()["underlyings"]) == 3
    assert res_single.json()["fees"]["total_fee_pct"] == 0.80


def test_api_sld_underlyings():
    res = client.get("/api/sld/products/PRD-101/underlyings")
    assert res.status_code == 200
    data = res.json()
    assert data["isin"] == "CH1261564201"
    assert len(data["underlyings"]) == 3

    # Query param endpoint
    res = client.get("/api/sld/underlyings?product_id=RFQ-102")
    assert res.status_code == 200
    assert len(res.json()["underlyings"]) == 3

    # Filter underlyings by ticker
    res_ticker = client.get("/api/sld/underlyings?ticker=NESN")
    assert res_ticker.status_code == 200
    assert isinstance(res_ticker.json(), list)
    assert len(res_ticker.json()) > 0


def test_api_sld_fees():
    res = client.get("/api/sld/products/CH1261564201/fees")
    assert res.status_code == 200
    data = res.json()
    assert data["total_fee_pct"] == 0.80

    # Query param endpoint
    res = client.get("/api/sld/fees?product_id=RFQ-103")
    assert res.status_code == 200
    assert res.json()["total_fee_pct"] == 0.52

    # Query across products with fee filter
    res_filtered = client.get("/api/sld/fees?max_total_fee_pct=0.60")
    assert res_filtered.status_code == 200
    assert isinstance(res_filtered.json(), list)
    assert all(f["total_fee_pct"] <= 0.60 for f in res_filtered.json())


def test_api_sld_not_found():
    res = client.get("/api/sld/products/NONEXISTENT/underlyings")
    assert res.status_code == 404

    res_p = client.get("/api/sld/products/NONEXISTENT")
    assert res_p.status_code == 404
