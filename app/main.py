from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import chat, items, sld

app = FastAPI(
    title="SLD Structured Products Chatbot & API",
    description="FastAPI chatbot and mock REST APIs for SLD RFQ distribution and structured products pricing.",
    version="1.0.0",
)
app.include_router(items.router)
app.include_router(chat.router)
app.include_router(sld.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
