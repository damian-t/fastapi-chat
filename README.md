# IH Trading Data Chatbot & REST API

FastAPI chatbot and mock REST tools for **IH Trading Data Chatbot**, currently distributing and answering Requests for Quotes (RFQs), underlying basket performance, and fee schedules for structured products using SLD data.

The API supports **three execution modes**:
1. **Mock LLM (`mock`)**: Fast, deterministic local simulated agent with multi-turn iterative reasoning.
2. **Gemini 3.8 Flash Native Tools (`gemini-native`)**: Native API function-calling powered by Google Gemini 3.8 Flash (`gemini-3.8-flash`) using standard `tools` parameter and preserving thought signatures across turns.
3. **Gemini 3.8 Flash Prompt Mode (`gemini`)**: Real LLM interaction powered by Google Gemini 3.8 Flash (`gemini-3.8-flash`) using prompt-based tool reasoning (no function-calling API, descriptions in context, multi-turn iteration).

---

## Quickstart

### 1. Install & Configure
```bash
pip install -r requirements.txt
```

Set your API key (if using Gemini mode):
```bash
export GOOGLE_API_KEY="your-google-api-key"
# or
export GEMINI_API_KEY="your-gemini-api-key"
```

Configure default mode via environment variable (optional, defaults to `mock`):
```bash
export LLM_MODE=gemini # or "mock"
```

### 2. Run the Server
```bash
uvicorn app.main:app --reload
```
- Interactive Swagger docs: `http://127.0.0.1:8000/docs`
- Modern Chat UI: `http://127.0.0.1:8000/`

---

## Operating Modes

### Mode 1: Mock LLM (`mock`)
- Model reported: `mock-sld-llm-v2`
- Deterministic heuristic agent that detects intents, plans sequential tool executions, evaluates sufficiency, and formats financial interpretations.
- Runs without any API key or external network dependency.

### Mode 2: Gemini 3.8 Flash Native Tools (`gemini-native`)
- Model reported: `gemini-3.8-flash`
- **Native function calling**: Passes standard OpenAI-compatible `tools` specifications to Gemini's API.
- **Workflow**:
  1. The API sends `messages` and `tools` to Gemini.
  2. Gemini emits native function calls (`tool_calls` with IDs and `thought_signature`).
  3. The backend executes the corresponding function(s) against SLD data.
  4. The backend sends tool execution results (`role: "tool"`, `tool_call_id`) back to Gemini.
  5. Gemini evaluates the tool response, making follow-up calls if needed, or generates the final markdown interpretation.

### Mode 3: Gemini 3.8 Flash Prompt Mode (`gemini`)
- Model reported: `gemini-3.8-flash`
- **Prompt-only tool calling**: The LLM interacts strictly through prompt context containing descriptions of the 3 SLD tools.
- **Workflow**:
  1. The backend provides the system prompt and tool definitions in the LLM's context.
  2. Gemini figures out whether tools are needed and outputs a structured JSON plan with parameters.
  3. The backend executes the corresponding function(s) against SLD data.
  4. The backend sends the execution results back to Gemini along with the original user query.
  5. Gemini evaluates the new data against the user query. If more calls are needed (multi-step dependency), it outputs the next tool call; otherwise, it answers the question and interprets the financial metrics.

---

## Selecting Modes via API

`POST /api/chat` accepts an optional `mode` property:

```json
{
  "message": "Show all open RFQs in USD",
  "mode": "gemini"
}
```

Or for mock mode:
```json
{
  "message": "What are the fees for product CH1261564201?",
  "mode": "mock"
}
```

Query available modes:
```bash
curl http://127.0.0.1:8000/api/chat/modes
```

---

## Integrated SLD Tools & REST Endpoints

1. **`get_rfqs(start_date, end_date, isin, valor, currency, status, issuer, product_type, underlying, rfq_id, limit, offset)`**
   - REST: `GET /api/sld/rfqs` (alias: `GET /api/sld/products`)
   - Supports search period bounds (`start_date`, `end_date`), security identifiers (`isin`, `valor`, `rfq_id`), and subset filters (`currency`, `status`, `issuer`, `product_type`, `underlying`) with pagination (`limit`, `offset`).
   - LLM Tool Calling: returns a bounded, compact summary representation by default (`limit=10`, `compact=True`) with envelope metadata (`total_count`, `returned_count`, `has_more`) to keep the LLM context window bounded.
2. **`get_underlyings_for_product(product_id)`**
   - REST: `GET /api/sld/products/{product_id}/underlyings` (or `GET /api/sld/underlyings?product_id=...`)
   - Takes `product_id` (mandatory). Returns underlying basket constituents. Supports Product ID, Valor, ISIN, or RFQ ID.
3. **`get_fees_for_product(product_id)`**
   - REST: `GET /api/sld/products/{product_id}/fees` (or `GET /api/sld/fees?product_id=...`)
   - Takes `product_id` (mandatory). Returns structured product fee schedules (distribution, structuring, management, exchange fees). Supports Product ID, Valor, ISIN, or RFQ ID.

---

## Mock Dataset (CSV)

The mock dataset provides **100 plausible structured product RFQs** loaded from CSV:
- **Master Dataset**: `app/data/rfq_products.csv` (100 RFQ products with attributes, multi-quote issuer pricing, underlyings, and fee schedules)
- **Normalized Datasets**: `app/data/underlyings.csv` (all constituent assets) and `app/data/fees.csv` (fee schedules)
- **Data Generator**: `scripts/generate_mock_dataset.py` reproduces the dataset with deterministic attributes, realistic Swiss/US/European equities and indices, diverse product structures (BRCs, Autocallables, Capital Protection, Reverse Convertibles, etc.), and multi-issuer pricing quotes.
- `SLDService` parses the CSV on startup and exposes `get_rfqs`, `get_underlyings_for_product`, and `get_fees_for_product`.

---

## Running Tests

Run full test suite (unit tests, mock agent tests, prompt tool extraction tests, and live Gemini tests):
```bash
pytest
```
