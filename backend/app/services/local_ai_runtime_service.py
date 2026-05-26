from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import requests

from app.core.config import settings
from app.services.ollama_health_service import get_ollama_health

logger = logging.getLogger(__name__)

LOCAL_ENGINE_OFFLINE = "LOCAL_ENGINE_OFFLINE"
LOCAL_MODEL_MISSING = "LOCAL_MODEL_MISSING"
LOCAL_ENGINE_TIMEOUT = "LOCAL_ENGINE_TIMEOUT"
LOCAL_ENGINE_BUSY = "LOCAL_ENGINE_BUSY"
LOCAL_ENGINE_ERROR = "LOCAL_ENGINE_ERROR"

CHAT_BUSY_MESSAGE = "The local AI engine is busy. Please try again in a moment."
GENERATION_BUSY_MESSAGE = "Draft generation is currently running locally. Please wait until it finishes, or try again later."
TIMEOUT_MESSAGE = "The local AI engine took too long to respond. Try again in a moment."
OFFLINE_MESSAGE = "The local AI engine is currently offline. Start the local engine and try again. Your document remains on this machine."
MODEL_MISSING_MESSAGE = "A required local model is missing. Pull the model and try again."
ERROR_MESSAGE = "The local AI engine encountered an error. Please try again in a moment."


@dataclass
class OperationClaim:
    kind: str
    token: str
    owns_lock: bool


@dataclass
class LocalAiErrorResult:
    ok: bool
    code: str
    message: str
    external_api_used: bool = False


class _RuntimeState:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._current_kind: str | None = None
        self._current_token: str | None = None
        self._started_at: float | None = None

    def acquire(self, kind: str, wait_seconds: float = 0.0, owner_token: str | None = None) -> OperationClaim | None:
        with self._condition:
            if owner_token and owner_token == self._current_token:
                return OperationClaim(kind=kind, token=owner_token, owns_lock=False)

            if self._current_kind is None:
                token = uuid.uuid4().hex
                self._current_kind = kind
                self._current_token = token
                self._started_at = time.perf_counter()
                return OperationClaim(kind=kind, token=token, owns_lock=True)

            if self._should_fail_fast(kind):
                return None

            deadline = time.perf_counter() + max(wait_seconds, 0.0)
            while self._current_kind is not None and time.perf_counter() < deadline:
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    break
                self._condition.wait(timeout=min(remaining, 0.5))

            if self._current_kind is not None:
                return None

            token = uuid.uuid4().hex
            self._current_kind = kind
            self._current_token = token
            self._started_at = time.perf_counter()
            return OperationClaim(kind=kind, token=token, owns_lock=True)

    def release(self, claim: OperationClaim | None) -> None:
        if claim is None or not claim.owns_lock:
            return
        with self._condition:
            if self._current_token == claim.token:
                self._current_kind = None
                self._current_token = None
                self._started_at = None
                self._condition.notify_all()

    def current_kind(self) -> str | None:
        with self._condition:
            return self._current_kind

    def current_token(self) -> str | None:
        with self._condition:
            return self._current_token

    def _should_fail_fast(self, requested_kind: str) -> bool:
        if self._current_kind == "generation" and requested_kind == "chat":
            return True
        return False


_runtime_state = _RuntimeState()


@contextmanager
def claim_operation(kind: str, wait_seconds: float = 0.0, owner_token: str | None = None) -> Iterator[OperationClaim | None]:
    claim = _runtime_state.acquire(kind, wait_seconds=wait_seconds, owner_token=owner_token)
    try:
        yield claim
    finally:
        _runtime_state.release(claim)


def current_operation_kind() -> str | None:
    return _runtime_state.current_kind()


def current_operation_token() -> str | None:
    return _runtime_state.current_token()


def classify_local_ai_error(error: Exception | str | None, *, response_text: str | None = None, status_code: int | None = None) -> LocalAiErrorResult:
    if status_code in {409, 423, 429}:
        return LocalAiErrorResult(ok=False, code=LOCAL_ENGINE_BUSY, message=CHAT_BUSY_MESSAGE)

    text = _normalize_error_text(error, response_text)
    if not text:
        return LocalAiErrorResult(ok=False, code=LOCAL_ENGINE_ERROR, message=ERROR_MESSAGE)

    if any(signal in text for signal in ["connection refused", "connect refused", "failed to establish a new connection", "connection reset", "remote disconnected", "ollama is not running"]):
        return LocalAiErrorResult(ok=False, code=LOCAL_ENGINE_OFFLINE, message=OFFLINE_MESSAGE)
    if any(signal in text for signal in ["timed out", "timeout", "read timeout", "connect timeout"]):
        return LocalAiErrorResult(ok=False, code=LOCAL_ENGINE_TIMEOUT, message=TIMEOUT_MESSAGE)
    if any(signal in text for signal in ["model missing", "not found", "model is not available", "no such model"]):
        return LocalAiErrorResult(ok=False, code=LOCAL_MODEL_MISSING, message=MODEL_MISSING_MESSAGE)
    if any(signal in text for signal in ["busy", "locked", "already in use", "another request", "queue full"]):
        return LocalAiErrorResult(ok=False, code=LOCAL_ENGINE_BUSY, message=CHAT_BUSY_MESSAGE)

    return LocalAiErrorResult(ok=False, code=LOCAL_ENGINE_ERROR, message=ERROR_MESSAGE)


def build_unavailable_result(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "code": code,
        "error": message,
        "message": message,
        "external_api_used": False,
        "provider": "local_ollama",
    }


def run_ollama_chat(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float = 0.2,
    timeout: int = 120,
    owner_token: str | None = None,
) -> dict[str, Any]:
    health = get_ollama_health()
    if not health.get("available"):
        message = health.get("message") or OFFLINE_MESSAGE
        return build_unavailable_result(LOCAL_ENGINE_OFFLINE, message)
    if not health.get("chat_model_available"):
        message = health.get("message") or MODEL_MISSING_MESSAGE
        return build_unavailable_result(LOCAL_MODEL_MISSING, message)

    claim = None
    if owner_token and owner_token == current_operation_token():
        claim = OperationClaim(kind="chat", token=owner_token, owns_lock=False)
    else:
        claim = _runtime_state.acquire("chat", wait_seconds=2.0, owner_token=owner_token)
        if claim is None:
            message = GENERATION_BUSY_MESSAGE if current_operation_kind() == "generation" else CHAT_BUSY_MESSAGE
            code = LOCAL_ENGINE_BUSY if current_operation_kind() == "generation" else LOCAL_ENGINE_BUSY
            return build_unavailable_result(code, message)

    started = time.perf_counter()
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }

    try:
        response = requests.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=timeout)
        if response.status_code == 404:
            return build_unavailable_result(LOCAL_MODEL_MISSING, response.text or MODEL_MISSING_MESSAGE)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            result = classify_local_ai_error(exc, response_text=response.text, status_code=response.status_code)
            logger.warning("local chat failed: code=%s message=%s", result.code, result.message)
            return {
                "ok": False,
                "code": result.code,
                "error": result.message,
                "message": result.message,
                "provider": "local_ollama",
                "model_used": model,
                "external_api_used": False,
            }

        data = response.json()
        elapsed = round(time.perf_counter() - started, 2)
        logger.info("provider=local_ollama model=%s elapsed_seconds=%.2f", model, elapsed)
        return {
            "ok": True,
            "text": data.get("message", {}).get("content", "").strip(),
            "provider": "local_ollama",
            "model_used": model,
            "elapsed_seconds": elapsed,
            "external_api_used": False,
        }
    except requests.Timeout as exc:
        result = classify_local_ai_error(exc)
        logger.warning("local chat timeout: %s", exc)
        return {
            "ok": False,
            "code": result.code,
            "error": result.message,
            "message": result.message,
            "provider": "local_ollama",
            "model_used": model,
            "external_api_used": False,
        }
    except requests.RequestException as exc:
        result = classify_local_ai_error(exc)
        logger.warning("local chat request failed: %s", exc)
        return {
            "ok": False,
            "code": result.code,
            "error": result.message,
            "message": result.message,
            "provider": "local_ollama",
            "model_used": model,
            "external_api_used": False,
        }
    finally:
        _runtime_state.release(claim)


def post_ollama_json(path: str, payload: dict[str, Any], *, timeout: int = 120) -> dict[str, Any]:
    health = get_ollama_health()
    if not health.get("available"):
        raise ValueError(health.get("message") or OFFLINE_MESSAGE)
    response = requests.post(f"{settings.OLLAMA_BASE_URL}{path}", json=payload, timeout=timeout)
    if response.status_code == 404:
        raise ValueError(MODEL_MISSING_MESSAGE)
    response.raise_for_status()
    return response.json()


def _normalize_error_text(error: Exception | str | None, response_text: str | None = None) -> str:
    parts = []
    if isinstance(error, Exception):
        parts.append(str(error))
        if getattr(error, "__cause__", None) is not None:
            parts.append(str(error.__cause__))
    elif error:
        parts.append(str(error))
    if response_text:
        parts.append(response_text)
    return " ".join(parts).lower()
