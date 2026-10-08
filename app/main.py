from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import chat, items, sld

app = FastAPI(
    title="IH Trading Data Chatbot",
    description="FastAPI service and chatbot for IH trading data (currently powered by SLD data).",
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
