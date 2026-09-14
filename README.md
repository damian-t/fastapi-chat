# Minimal FastAPI example + chat frontend

Run from this directory:

```bash
uvicorn app.main:app --reload
```

Open the chat UI:

- `http://127.0.0.1:8000/`

Endpoints:

- `GET /health`
- `POST /api/chat` — dummy LLM chat endpoint used by the frontend
- `GET /items`
- `POST /items`
- `GET /items/{item_id}`

Interactive docs: `http://127.0.0.1:8000/docs`

The chat frontend lives in `app/static/` and posts JSON to `/api/chat`. Replace `app/services/llm_service.py` with a real LLM client when ready.
