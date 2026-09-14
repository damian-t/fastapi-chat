from app.models.chat import ChatMessage


class DummyLLMService:
    """Swap this service for a real LLM client later."""

    model_name = "dummy-llm-v0"

    async def generate_reply(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> str:
        text = message.strip()
        history_count = len(history or [])
        lower = text.lower()

        if lower in {"hi", "hello", "hey", "hallo", "hoi"}:
            return "Hello! I am the dummy LLM behind this FastAPI chat. Ask me anything."
        if "help" in lower:
            return (
                "This chat UI posts your text to POST /api/chat. "
                "The router calls DummyLLMService.generate_reply, which you can replace "
                "with a real model call later."
            )
        if lower.endswith("?"):
            return (
                f"Dummy answer: I would normally send your question {text!r} "
                f"plus {history_count} previous message(s) to an LLM. "
                "For now, this is a canned response."
            )
        return (
            f"Dummy LLM received {text!r} with {history_count} previous message(s). "
            "Replace DummyLLMService.generate_reply with a real LLM integration."
        )


dummy_llm_service = DummyLLMService()
