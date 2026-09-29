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
    assert len(data) == 5

    # Filter status
    res = client.get("/api/sld/rfqs?status=open")
    assert res.status_code == 200
    assert len(res.json()) == 2

    # Filter currency
    res = client.get("/api/sld/rfqs?currency=CHF")
    assert res.status_code == 200
    assert len(res.json()) == 2


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


def test_api_sld_fees():
    res = client.get("/api/sld/products/CH1261564201/fees")
    assert res.status_code == 200
    data = res.json()
    assert data["total_fee_pct"] == 0.80

    # Query param endpoint
    res = client.get("/api/sld/fees?product_id=RFQ-103")
    assert res.status_code == 200
    assert res.json()["total_fee_pct"] == 0.52


def test_api_sld_not_found():
    res = client.get("/api/sld/products/NONEXISTENT/underlyings")
    assert res.status_code == 404
