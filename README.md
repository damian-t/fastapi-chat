# SLD Structured Products Chatbot & REST API

FastAPI chatbot and mock REST tools for **SLD**, an application that distributes and answers Requests for Quotes (RFQs) for structured products.

## Run
```bash
uvicorn app.main:app --reload
```
Interactive docs: `http://127.0.0.1:8000/docs`  
Chat UI: `http://127.0.0.1:8000/`

## Integrated SLD Tools & REST Endpoints

1. **`get_rfqs(rfq_id, status, issuer, product_type, currency, limit)`**
   - REST: `GET /api/sld/rfqs`
   - Filters RFQs by ID, status (`open`, `quoted`, `traded`, `expired`, `rejected`), currency, product structure, or issuer quote.
2. **`get_underlyings_of_product(product_id)`**
   - REST: `GET /api/sld/products/{product_id}/underlyings` (or `GET /api/sld/underlyings?product_id=...`)
   - Returns underlying basket constituents, spots, current prices, strikes, barrier levels, and breach checks. Supports Product ID, ISIN, or RFQ ID.
3. **`get_fees_of_product(product_id, fee_type)`**
   - REST: `GET /api/sld/products/{product_id}/fees` (or `GET /api/sld/fees?product_id=...`)
   - Returns structured product fee schedules (distribution fee, structuring fee, recurring management fee, exchange fee, monetary amounts).

## Chatbot Agent Flow (`POST /api/chat`)
1. **Understands Intent:** Parses the user question to detect RFQ queries, underlying requests, fee breakdowns, or multi-tool combinations.
2. **Extracts Parameters:** Identifies identifiers (`RFQ-101`, `CH1261564201`, etc.), lifecycle status (`open`, `traded`), currency (`USD`, `CHF`), product types, and carries over conversational context.
3. **Executes Tools:** Calls the relevant mock service methods.
4. **Interprets Results:** Synthesizes financial metrics (spreads, coupons, barrier safety, fee totals) and returns a human-readable response alongside structured tool call records.

## Tests
```bash
pytest
```
