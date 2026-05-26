import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services.chunking_service import create_chunks_for_rfp
from app.services.classification_service import classify_document
from app.services.parsing_service import extract_text_from_file


SAMPLE_TEXT = """
Request for Proposal: Private Document Analysis Tool

The buyer is seeking a local-first software system for reviewing RFP documents. The solution must run on Windows laptops,
store uploaded documents locally, extract text from PDF, DOCX, and TXT files, and support private question answering using
a locally hosted Ollama model.

Scope of work includes document upload, deterministic document quality classification, chunking, lexical retrieval, and a
private chat endpoint. The vendor must not transmit document contents to external APIs. The proposed MVP should be simple,
auditable, and suitable for future expansion.

Evaluation criteria include privacy, ease of installation, clear API contracts, document handling reliability, and a path
to future local embeddings. The implementation should avoid heavyweight background processing during the MVP.
""" * 3


def main() -> None:
    init_db()
    sample_path = Path("scratch/sample_rfp.txt")
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_text(SAMPLE_TEXT, encoding="utf-8")

    parsed = extract_text_from_file(str(sample_path))
    classification = classify_document(
        int(parsed["page_count"]),
        int(parsed["word_count"]),
        int(parsed["character_count"]),
        str(parsed["text"]),
    )

    db = SessionLocal()
    try:
        rfp = RFPDocument(
            title="Sample RFP",
            original_filename=sample_path.name,
            stored_filename=sample_path.name,
            file_path=str(sample_path),
            file_type="txt",
            file_size=sample_path.stat().st_size,
            page_count=int(parsed["page_count"]),
            word_count=int(parsed["word_count"]),
            character_count=int(parsed["character_count"]),
            line_count=int(parsed["line_count"]),
            extracted_text=str(parsed["text"]),
            document_quality=classification["document_quality"],
            classification_reason=classification["reason"],
            status=classification["status"],
        )
        db.add(rfp)
        db.commit()
        db.refresh(rfp)
        chunk_count = create_chunks_for_rfp(db, rfp.id, rfp.extracted_text or "")
        print({"rfp_id": rfp.id, "classification": classification, "chunk_count": chunk_count})
    finally:
        db.close()


if __name__ == "__main__":
    main()
