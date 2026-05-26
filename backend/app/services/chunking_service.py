from sqlalchemy.orm import Session

from app.models.rfp import RFPChunk
from app.utils.text_utils import count_words, normalize_text


def chunk_text(text: str, max_words: int = 900, overlap_words: int = 120) -> list[dict[str, int | str | None]]:
    paragraphs = [p.strip() for p in normalize_text(text).split("\n\n") if p.strip()]
    chunks: list[dict[str, int | str | None]] = []
    current_words: list[str] = []

    for paragraph in paragraphs:
        paragraph_words = paragraph.split()
        if current_words and len(current_words) + len(paragraph_words) > max_words:
            chunks.append(_build_chunk(chunks, current_words))
            overlap = current_words[-overlap_words:] if overlap_words > 0 else []
            current_words = overlap + paragraph_words
        else:
            current_words.extend(paragraph_words)

    if current_words:
        chunks.append(_build_chunk(chunks, current_words))

    return chunks


def create_chunks_for_rfp(db: Session, rfp_id: int, text: str) -> int:
    db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).delete()
    for chunk in chunk_text(text):
        db.add(
            RFPChunk(
                rfp_id=rfp_id,
                chunk_order=int(chunk["chunk_order"]),
                page_number=None,
                section_title=None,
                chunk_text=str(chunk["chunk_text"]),
                word_count=int(chunk["word_count"]),
            )
        )
    db.commit()
    return db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).count()


def _build_chunk(existing_chunks: list[dict[str, int | str | None]], words: list[str]) -> dict[str, int | str | None]:
    return {
        "chunk_order": len(existing_chunks) + 1,
        "page_number": None,
        "section_title": None,
        "chunk_text": " ".join(words).strip(),
        "word_count": count_words(" ".join(words)),
    }
