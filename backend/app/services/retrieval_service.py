import re

from sqlalchemy.orm import Session

from app.models.rfp import RFPChunk
from app.services.vector_store_service import search_by_embedding
from app.utils.text_utils import safe_preview


def search_chunks(
    db: Session,
    rfp_id: int,
    query: str,
    top_k: int = 5,
    mode: str = "hybrid",
) -> list[dict[str, int | str | float | None]]:
    normalized_mode = mode.lower().strip()
    if normalized_mode == "vector":
        return _search_vector_with_fallback(db, rfp_id, query, top_k)
    if normalized_mode == "lexical":
        return _search_lexical(db, rfp_id, query, top_k, retrieval_type="lexical")
    return _search_hybrid(db, rfp_id, query, top_k)


def _search_hybrid(db: Session, rfp_id: int, query: str, top_k: int) -> list[dict[str, int | str | float | None]]:
    vector_results = _try_vector_search(db, rfp_id, query, top_k)
    lexical_results = _search_lexical(db, rfp_id, query, top_k, retrieval_type="lexical")

    if not vector_results:
        for result in lexical_results:
            result["retrieval_type"] = "lexical_fallback"
        return lexical_results[:top_k]

    merged: dict[int, dict[str, int | str | float | None]] = {}
    for result in vector_results:
        merged[int(result["chunk_id"])] = {**result, "retrieval_type": "hybrid"}
    for result in lexical_results:
        chunk_id = int(result["chunk_id"])
        if chunk_id in merged:
            merged[chunk_id]["score"] = float(merged[chunk_id]["score"]) + min(float(result["score"]) / 100.0, 0.2)
        else:
            merged[chunk_id] = result

    return sorted(merged.values(), key=lambda item: float(item["score"]), reverse=True)[:top_k]


def _search_vector_with_fallback(db: Session, rfp_id: int, query: str, top_k: int) -> list[dict[str, int | str | float | None]]:
    vector_results = _try_vector_search(db, rfp_id, query, top_k)
    if vector_results:
        return vector_results
    fallback = _search_lexical(db, rfp_id, query, top_k, retrieval_type="lexical_fallback")
    return fallback


def _try_vector_search(db: Session, rfp_id: int, query: str, top_k: int) -> list[dict[str, int | str | float | None]]:
    has_embeddings = (
        db.query(RFPChunk)
        .filter(RFPChunk.rfp_id == rfp_id, RFPChunk.embedding_status == "completed", RFPChunk.embedding_json.isnot(None))
        .first()
        is not None
    )
    if not has_embeddings:
        return []
    try:
        return search_by_embedding(db, rfp_id, query, top_k)
    except Exception:
        return []


def _search_lexical(
    db: Session,
    rfp_id: int,
    query: str,
    top_k: int,
    retrieval_type: str,
) -> list[dict[str, int | str | float | None]]:
    terms = _terms(query)
    phrase = query.strip().lower()
    if not terms:
        return []

    scored_chunks = []
    chunks = db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).order_by(RFPChunk.chunk_order).all()
    for chunk in chunks:
        text_lower = chunk.chunk_text.lower()
        score = sum(text_lower.count(term) for term in terms)
        if phrase and phrase in text_lower:
            score += 5
        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: (item[0], -item[1].chunk_order), reverse=True)
    return [_serialize_chunk(chunk, float(score), retrieval_type) for score, chunk in scored_chunks[:top_k]]


def _terms(query: str) -> list[str]:
    return [term for term in re.findall(r"\b\w+\b", query.lower()) if len(term) > 2]


def _serialize_chunk(chunk: RFPChunk, score: float, retrieval_type: str) -> dict[str, int | str | float | None]:
    return {
        "chunk_id": chunk.id,
        "chunk_order": chunk.chunk_order,
        "section_title": chunk.section_title,
        "page_number": chunk.page_number,
        "score": score,
        "retrieval_type": retrieval_type,
        "chunk_text": chunk.chunk_text,
        "preview": safe_preview(chunk.chunk_text),
    }
