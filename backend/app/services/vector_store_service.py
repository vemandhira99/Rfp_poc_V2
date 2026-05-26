import json
import math

from sqlalchemy.orm import Session

from app.models.rfp import RFPChunk
from app.services.local_embedding_service import embed_text
from app.utils.text_utils import safe_preview


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def search_by_embedding(db: Session, rfp_id: int, query: str, top_k: int = 5) -> list[dict[str, int | str | float | None]]:
    query_vector = embed_text(query)
    if not query_vector:
        return []

    scored_chunks = []
    chunks = (
        db.query(RFPChunk)
        .filter(RFPChunk.rfp_id == rfp_id, RFPChunk.embedding_status == "completed", RFPChunk.embedding_json.isnot(None))
        .order_by(RFPChunk.chunk_order)
        .all()
    )
    for chunk in chunks:
        try:
            chunk_vector = [float(value) for value in json.loads(chunk.embedding_json or "[]")]
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        score = cosine_similarity(query_vector, chunk_vector)
        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    return [_serialize_vector_chunk(chunk, float(score)) for score, chunk in scored_chunks[:top_k]]


def _serialize_vector_chunk(chunk: RFPChunk, score: float) -> dict[str, int | str | float | None]:
    return {
        "chunk_id": chunk.id,
        "chunk_order": chunk.chunk_order,
        "section_title": chunk.section_title,
        "page_number": chunk.page_number,
        "score": score,
        "retrieval_type": "vector",
        "chunk_text": chunk.chunk_text,
        "preview": safe_preview(chunk.chunk_text),
    }
