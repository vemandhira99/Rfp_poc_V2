import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.rfp import RFPChunk
from app.services.ollama_health_service import EMBEDDING_MODEL, get_ollama_health
from app.services.local_ai_runtime_service import classify_local_ai_error, post_ollama_json

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_MISSING = "Run: ollama pull nomic-embed-text"
MAX_EMBED_CHARS = 8000


def check_embedding_model() -> dict[str, Any]:
    health = get_ollama_health()
    return {
        "available": bool(health.get("embedding_model_available")),
        "models": health.get("models", []),
        "configured_embedding_model": settings.OLLAMA_EMBED_MODEL,
        "message": None
        if health.get("embedding_model_available")
        else health.get("message")
        or EMBEDDING_MODEL_MISSING,
        "details": health.get("details"),
    }


def embed_text(text: str, model: str | None = None) -> list[float]:
    selected_model = model or settings.OLLAMA_EMBED_MODEL
    input_text = text.strip()[:MAX_EMBED_CHARS]
    if not input_text:
        return []
    health = get_ollama_health()
    if not health.get("available"):
        raise ValueError(health.get("message") or "Ollama is offline.")
    if not health.get("embedding_model_available"):
        raise ValueError(health.get("message") or EMBEDDING_MODEL_MISSING)

    try:
        vector = _embed_with_api_embed(input_text, selected_model)
    except Exception as exc:
        fallback_error = classify_local_ai_error(exc)
        if fallback_error.code in {"LOCAL_ENGINE_OFFLINE", "LOCAL_MODEL_MISSING", "LOCAL_ENGINE_TIMEOUT", "LOCAL_ENGINE_BUSY"}:
            raise ValueError(fallback_error.message) from exc
        try:
            vector = _embed_with_api_embeddings(input_text, selected_model)
        except Exception as fallback_exc:
            classified = classify_local_ai_error(fallback_exc)
            raise ValueError(classified.message) from fallback_exc

    logger.info("provider=local_ollama_embedding model=%s", selected_model)
    return vector


def embed_chunks_for_rfp(db: Session, rfp_id: int) -> dict[str, int | str]:
    health = get_ollama_health()
    if not health.get("available"):
        raise ValueError(health.get("message") or "Ollama is offline.")
    if not health.get("embedding_model_available"):
        raise ValueError(health.get("message") or EMBEDDING_MODEL_MISSING)

    chunks = db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).order_by(RFPChunk.chunk_order).all()
    embedded_chunks = 0
    failed_chunks = 0

    for chunk in chunks:
        if chunk.embedding_json and chunk.embedding_status == "completed":
            embedded_chunks += 1
            continue

        try:
            vector = embed_text(chunk.chunk_text)
            if not vector:
                raise ValueError("Embedding vector was empty.")
            chunk.embedding_json = json.dumps(vector)
            chunk.embedding_model = settings.OLLAMA_EMBED_MODEL
            chunk.embedding_status = "completed"
            embedded_chunks += 1
        except Exception as exc:
            logger.warning("Embedding failed for rfp_id=%s chunk_id=%s: %s", rfp_id, chunk.id, exc)
            chunk.embedding_status = "failed"
            failed_chunks += 1
        finally:
            db.add(chunk)
            db.commit()

    return {
        "rfp_id": rfp_id,
        "total_chunks": len(chunks),
        "embedded_chunks": embedded_chunks,
        "failed_chunks": failed_chunks,
        "model": settings.OLLAMA_EMBED_MODEL,
    }


def _embed_with_api_embed(text: str, model: str) -> list[float]:
    data = post_ollama_json("/api/embed", {"model": model, "input": text}, timeout=120)
    embeddings = data.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, list):
            return [float(value) for value in first]
    embedding = data.get("embedding")
    if isinstance(embedding, list):
        return [float(value) for value in embedding]
    raise ValueError("Ollama /api/embed did not return an embedding vector.")


def _embed_with_api_embeddings(text: str, model: str) -> list[float]:
    embedding = post_ollama_json("/api/embeddings", {"model": model, "prompt": text}, timeout=120).get("embedding")
    if isinstance(embedding, list):
        return [float(value) for value in embedding]
    raise ValueError("Ollama /api/embeddings did not return an embedding vector.")
