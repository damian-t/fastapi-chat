from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_greeting():
    res = client.post("/api/chat", json={"message": "Hello!"})
    assert res.status_code == 200
    data = res.json()
    assert "SLD Structured Products Assistant" in data["reply"]
    assert len(data["tool_calls"]) == 0


def test_chat_help():
    res = client.post("/api/chat", json={"message": "What can you do?"})
    assert res.status_code == 200
    data = res.json()
    assert "get_rfqs" in data["reply"]
    assert "get_underlyings_of_product" in data["reply"]
    assert "get_fees_of_product" in data["reply"]


def test_chat_open_rfqs():
    res = client.post("/api/chat", json={"message": "Show me all open RFQs in USD"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_rfqs"
    assert call["parameters"].get("status") == "open"
    assert call["parameters"].get("currency") == "USD"
    assert "RFQ-102" in data["reply"]


def test_chat_rfq_details():
    res = client.post("/api/chat", json={"message": "What quotes do we have for RFQ-101?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_rfqs"
    assert call["parameters"].get("rfq_id") == "RFQ-101"
    assert "Vontobel" in data["reply"]
    assert "ZKB" in data["reply"]


def test_chat_underlyings():
    res = client.post("/api/chat", json={"message": "What are the underlyings of RFQ-102?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_underlyings_of_product"
    assert call["parameters"].get("product_id") == "RFQ-102"
    assert "AAPL US" in data["reply"]
    assert "MSFT US" in data["reply"]
    assert "NVDA US" in data["reply"]


def test_chat_fees():
    res = client.post("/api/chat", json={"message": "What are the fees for product CH1261564201?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_fees_of_product"
    assert call["parameters"].get("product_id") == "CH1261564201"
    assert "0.80%" in data["reply"]
    assert "Distribution Fee" in data["reply"]


def test_chat_multi_tool():
    res = client.post(
        "/api/chat",
        json={"message": "Can you check the underlyings and fees for RFQ-104?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 2
    tool_names = [c["tool"] for c in data["tool_calls"]]
    assert "get_underlyings_of_product" in tool_names
    assert "get_fees_of_product" in tool_names
    assert "ABBN SW" in data["reply"]
    assert "Distribution Fee" in data["reply"]


def test_chat_context_carryover():
    history = [
        {"role": "user", "content": "Tell me about RFQ-101"},
        {"role": "assistant", "content": "RFQ-101 is a quoted BRC."},
    ]
    res = client.post(
        "/api/chat",
        json={"message": "What are its underlyings?", "history": history},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_underlyings_of_product"
    assert call["parameters"].get("product_id") == "RFQ-101"
    assert "NESN SW" in data["reply"]
