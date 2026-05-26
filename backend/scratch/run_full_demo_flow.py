import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import AuditLog, RFPDocument, RFPDraftSection
from app.services.docx_export_service import export_private_short_draft
from app.services.local_embedding_service import embed_chunks_for_rfp
from app.services.private_chat_service import answer_private_rfp_question
from app.services.private_generation_service import generate_private_short_draft
from scratch.demo_utils import create_demo_rfp


def main() -> None:
    init_db()
    db = SessionLocal()
    report = {}
    try:
        rfp = db.query(RFPDocument).filter(RFPDocument.status.in_(["ready_for_private_chat", "draft_generated"])).order_by(RFPDocument.created_at.desc()).first()
        rfp_id = rfp.id if rfp else create_demo_rfp(embed=False)
        report["rfp_id"] = rfp_id
        report["upload_ok"] = True
        report["embeddings"] = embed_chunks_for_rfp(db, rfp_id)
        chat = answer_private_rfp_question(db, rfp_id, "What is this RFP about?")
        report["chat_ok"] = chat.get("provider") == "local_ollama" and chat.get("external_api_used") is False
        existing = db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp_id).count()
        generation = generate_private_short_draft(db, rfp_id, confirm_regenerate=existing > 0)
        report["generation_ok"] = generation.get("sections_generated") == 8
        export = export_private_short_draft(db, rfp_id)
        path = Path(export["file_path"])
        report["export_ok"] = path.exists() and path.stat().st_size > 0
        report["audit_ok"] = db.query(AuditLog).filter(AuditLog.rfp_id == rfp_id).count() > 0
        report["external_api_used"] = False
        print(report)
    finally:
        db.close()


if __name__ == "__main__":
    main()
