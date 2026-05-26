from pathlib import Path

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services.chunking_service import create_chunks_for_rfp
from app.services.classification_service import classify_document
from app.services.local_embedding_service import embed_chunks_for_rfp
from app.services.parsing_service import extract_text_from_file


DEMO_TEXT = """
Request for Proposal: Secure Local RFP Intelligence Workspace

The buyer requires a private, local-first RFP analysis tool for uploading solicitation documents, extracting text, classifying document quality, generating embeddings, retrieving relevant excerpts, asking grounded questions, and producing a short first draft response. The system must run on a Windows laptop with no dedicated GPU and must not send RFP data to external AI providers.

Scope of work includes PDF, DOCX, and TXT ingestion, deterministic classification, local chunking, lexical fallback search, Ollama-based local embeddings, hybrid retrieval, private RFP chat, short draft generation, quality checks, DOCX export, audit logging, and local MCP tool access. The solution must support executive review, proposal team validation, and safe demo workflows.

Functional requirements include upload validation, document metadata tracking, chunk count visibility, source chunk references in chat, generation progress tracking, audit export, and clear privacy messaging. Technical requirements include FastAPI, SQLite for the local MVP, Next.js frontend, Ollama llama3.2:3b for chat, and nomic-embed-text for embeddings.

Security requirements include private mode operation, local-only storage, no cloud AI calls, no arbitrary shell execution, no arbitrary file access through MCP, no delete tools in MCP, and explicit confirmation before long-running draft generation. Human review is required for all generated content.

The expected MVP validation deadline is 30 June 2026. The vendor should describe approach, assumptions, risks, mitigations, implementation plan, support model, and next phase recommendations.
""" * 3


def create_demo_file() -> Path:
    path = Path("scratch/demo_private_rfp.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEMO_TEXT, encoding="utf-8")
    return path


def create_demo_rfp(embed: bool = True) -> int:
    init_db()
    path = create_demo_file()
    parsed = extract_text_from_file(str(path))
    classification = classify_document(
        int(parsed["page_count"]),
        int(parsed["word_count"]),
        int(parsed["character_count"]),
        str(parsed["text"]),
    )
    db = SessionLocal()
    try:
        rfp = RFPDocument(
            title="Demo Private RFP",
            original_filename=path.name,
            stored_filename=path.name,
            file_path=str(path),
            file_type="txt",
            file_size=path.stat().st_size,
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
        create_chunks_for_rfp(db, rfp.id, rfp.extracted_text or "")
        if embed:
            embed_chunks_for_rfp(db, rfp.id)
        return rfp.id
    finally:
        db.close()
