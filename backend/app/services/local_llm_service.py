import logging
from typing import Any

from app.core.config import settings
from app.services.ollama_health_service import EMBEDDING_MODEL, CHAT_MODEL, OFFLINE_MESSAGE, get_ollama_health
from app.services.local_ai_runtime_service import run_ollama_chat

logger = logging.getLogger(__name__)

OLLAMA_NOT_RUNNING = "Ollama is not running. Please start Ollama and pull llama3.2:3b."
MODEL_MISSING = "Local model is not available. Run: ollama pull llama3.2:3b"


def check_ollama_health() -> dict[str, Any]:
    health = get_ollama_health()
    return {
        "ok": bool(health.get("available")),
        "available": bool(health.get("available")),
        "chat_model_available": bool(health.get("chat_model_available")),
        "embedding_model_available": bool(health.get("embedding_model_available")),
        "chat_model": health.get("chat_model", CHAT_MODEL),
        "embedding_model": health.get("embedding_model", EMBEDDING_MODEL),
        "message": health.get("message", OFFLINE_MESSAGE),
        "details": health.get("details"),
        "models": health.get("models", []),
        "checked_at": health.get("checked_at"),
    }


def chat_local(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
    timeout: int = 120,
    runtime_token: str | None = None,
) -> dict[str, Any]:
    selected_model = model or settings.OLLAMA_CHAT_MODEL
    result = run_ollama_chat(messages, model=selected_model, temperature=temperature, timeout=timeout, owner_token=runtime_token)
    if result.get("ok"):
        return result
    return {
        "ok": False,
        "code": result.get("code"),
        "error": result.get("error") or result.get("message") or OLLAMA_NOT_RUNNING,
        "provider": "local_ollama",
        "model_used": selected_model,
        "external_api_used": False,
        "details": result.get("details"),
    }
