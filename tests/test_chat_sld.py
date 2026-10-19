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
    assert "102" in data["reply"] or "PRD-102" in data["reply"]


def test_chat_rfq_details():
    res = client.post("/api/chat", json={"message": "What details do we have for RFQ-101?"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_rfqs"
    assert call["parameters"].get("rfq_id") == "RFQ-101"
    assert "101" in data["reply"] or "CH1261564201" in data["reply"]


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
    assert "Distribution Fee" in data["reply"]
    assert "Structuring Fee" in data["reply"]


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
    assert "iterations" in data
    assert len(data["iterations"]) >= 1
    assert data["iterations"][0]["thought"] is not None


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
    assert data["tool_calls"][0]["tool"] == "get_underlyings_of_product"
    assert "NESN SW" in data["reply"]


def test_chat_date_based_search():
    res = client.post(
        "/api/chat",
        json={"message": "Show me RFQs from 2026-09-28 to 2026-09-29"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_rfqs"
    assert call["parameters"].get("start_date") == "2026-09-28"
    assert call["parameters"].get("end_date") == "2026-09-29"
    assert "Product #" in data["reply"] or "PRD-" in data["reply"]


def test_chat_subset_with_limit():
    res = client.post(
        "/api/chat",
        json={"message": "Show me the top 3 open RFQs in USD"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_rfqs"
    assert call["parameters"].get("status") == "open"
    assert call["parameters"].get("currency") == "USD"
    assert call["parameters"].get("limit") == 3
    assert "102" in data["reply"] or "PRD-102" in data["reply"]


def test_chat_subset_with_underlying():
    res = client.post(
        "/api/chat",
        json={"message": "Show me RFQs with underlying NESN"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "get_rfqs"
    assert call["parameters"].get("underlying") == "NESN"
    assert "NESN" in data["reply"]


def test_run_get_rfqs_compact_and_envelope():
    import json
    from app.services.llm_service import _run_get_rfqs, _serialize_tool_output
    from app.services.sld_service import sld_service

    # Full serialization size for all 100 products
    all_full = _serialize_tool_output(sld_service.get_rfqs())
    full_json_str = json.dumps(all_full)

    # Context-bounded compact call (default limit 10, compact=True)
    bounded_result = _run_get_rfqs({})
    bounded_json_str = json.dumps(bounded_result)

    assert bounded_result["total_count"] == 100
    assert bounded_result["returned_count"] == 10
    assert bounded_result["limit"] == 10
    assert bounded_result["has_more"] is True
    assert len(bounded_result["products"]) == 10

    # Verify significant token/character savings for LLM context
    assert len(bounded_json_str) < len(full_json_str) * 0.25

    # Verify subset filtering through _run_get_rfqs
    usd_open = _run_get_rfqs({"currency": "USD", "status": "open", "limit": 2})
    assert usd_open["returned_count"] == 2
    assert usd_open["total_count"] == 10
    assert usd_open["limit"] == 2
    assert usd_open["has_more"] is True
    for prod in usd_open["products"]:
        assert prod["currency"] == "USD"
        assert prod["status"] == "open"


def test_chat_token_usage_present_and_accurate():
    res = client.post("/api/chat", json={"message": "Show open RFQs in USD"})
    assert res.status_code == 200
    data = res.json()
    assert "token_usage" in data
    usage = data["token_usage"]
    assert usage is not None
    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
    assert usage["context_window_limit"] == 128000
    assert usage["context_window_used_pct"] > 0
    assert usage["cumulative_total_tokens"] >= usage["total_tokens"]


def test_chat_iteration_token_usage():
    res = client.post(
        "/api/chat",
        json={"message": "Can you check the underlyings and fees for RFQ-104?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "iterations" in data
    assert len(data["iterations"]) > 0
    for it in data["iterations"]:
        assert "token_usage" in it
        it_usage = it["token_usage"]
        assert it_usage is not None
        assert it_usage["prompt_tokens"] > 0
        assert it_usage["completion_tokens"] > 0
        assert it_usage["total_tokens"] > 0


def test_decimal_serialization_in_tool_calls_and_models():
    from decimal import Decimal
    from app.models.chat import ToolCallRecord, ChatResponse
    from app.services.llm_service import _serialize_tool_output, safe_json_dumps

    # Test recursive serialization of Decimals in dicts and lists
    nested_data = {
        "price": Decimal("102.3456"),
        "nested": [{"fee": Decimal("0.55")}, Decimal("1.23")],
    }
    serialized = _serialize_tool_output(nested_data)
    assert isinstance(serialized["price"], float)
    assert isinstance(serialized["nested"][0]["fee"], float)
    assert isinstance(serialized["nested"][1], float)

    # Test safe_json_dumps
    json_str = safe_json_dumps(nested_data)
    assert "102.3456" in json_str

    # Test ToolCallRecord auto-sanitization of Decimals
    record = ToolCallRecord(
        tool="mock_tool",
        parameters={"rate": Decimal("3.75")},
        result={"values": [Decimal("10.0"), Decimal("20.5")]},
    )
    assert isinstance(record.parameters["rate"], float)
    assert isinstance(record.result, dict)
    assert isinstance(record.result["values"][0], float)

    # Verify Pydantic ChatResponse serialization
    resp = ChatResponse(
        reply="Test reply",
        model="mock-test",
        tool_calls=[record],
    )
    dumped = resp.model_dump_json()
    assert "3.75" in dumped
    assert "20.5" in dumped


def test_chat_map_reduce_rfqs():
    res = client.post(
        "/api/chat",
        json={"message": "Can you do a map-reduce summary of all open RFQs in USD?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["tool_calls"]) == 1
    call = data["tool_calls"][0]
    assert call["tool"] == "map_reduce_rfqs"
    assert call["parameters"].get("status") == "open"
    assert call["parameters"].get("currency") == "USD"
    assert call["parameters"].get("batch_size") == 500
    assert "Server-Side Batch Map-Reduce Summary" in data["reply"]
    assert "Total Records Processed:" in data["reply"]
    assert "USD" in data["reply"]
    assert "token_usage" in data




