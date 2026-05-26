import logging
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

CHAT_MODEL = "llama3.2:3b"
EMBEDDING_MODEL = "nomic-embed-text"

OFFLINE_MESSAGE = "Ollama is offline. Start Ollama and pull the required local models."
CHAT_MODEL_MISSING_MESSAGE = f"Chat model missing. Run: ollama pull {CHAT_MODEL}"
EMBEDDING_MODEL_MISSING_MESSAGE = f"Embedding model missing. Run: ollama pull {EMBEDDING_MODEL}"


def get_ollama_health(explicit_test_prompt: bool = False) -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    try:
        response = requests.get(f"{base_url}/api/tags", timeout=8)
        response.raise_for_status()
        tags = response.json()
    except requests.RequestException as exc:
        return {
            "available": False,
            "chat_model_available": False,
            "embedding_model_available": False,
            "chat_model": CHAT_MODEL,
            "embedding_model": EMBEDDING_MODEL,
            "message": OFFLINE_MESSAGE,
            "checked_at": checked_at,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "details": str(exc),
        }

    models = [model.get("name") for model in tags.get("models", []) if model.get("name")]
    chat_model_available = _model_present(models, CHAT_MODEL)
    embedding_model_available = _model_present(models, EMBEDDING_MODEL)
    available = chat_model_available and embedding_model_available

    message = "Ollama is online with the required local models."
    if not chat_model_available and not embedding_model_available:
        message = "Chat and embedding models are missing."
    elif not chat_model_available:
        message = CHAT_MODEL_MISSING_MESSAGE
    elif not embedding_model_available:
        message = EMBEDDING_MODEL_MISSING_MESSAGE

    result: dict[str, Any] = {
        "available": available,
        "chat_model_available": chat_model_available,
        "embedding_model_available": embedding_model_available,
        "chat_model": CHAT_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "message": message,
        "checked_at": checked_at,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "models": models,
    }

    if explicit_test_prompt and available:
        result["test_prompt"] = _run_tiny_test_prompt(base_url)
    return result


def is_infrastructure_error(message: str | None) -> bool:
    if not message:
        return False
    lowered = message.lower()
    signals = [
        "ollama is not running",
        "ollama is offline",
        "model is not available",
        "model missing",
        "connection refused",
        "timeout",
        "timed out",
        "please start ollama",
        "traceback",
        "exception",
        "404 client error",
    ]
    return any(signal in lowered for signal in signals)


def _model_present(models: list[str], model_name: str) -> bool:
    return any(name == model_name or name == f"{model_name}:latest" for name in models)


def _run_tiny_test_prompt(base_url: str) -> str:
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": "Reply with exactly one word."},
                    {"role": "user", "content": "ok"},
                ],
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "").strip()
    except requests.RequestException as exc:
        logger.warning("Ollama tiny test prompt failed: %s", exc)
        return ""
