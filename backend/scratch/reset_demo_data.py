import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import AuditLog, ChatMessage, GenerationJob, RFPChunk, RFPDocument, RFPDraftExport, RFPDraftSection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete-exports", action="store_true")
    args = parser.parse_args()
    init_db()
    db = SessionLocal()
    try:
        demo_rfps = db.query(RFPDocument).filter(RFPDocument.original_filename.like("%demo%")).all()
        ids = [rfp.id for rfp in demo_rfps]
        if ids:
            db.query(ChatMessage).filter(ChatMessage.rfp_id.in_(ids)).delete(synchronize_session=False)
            db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id.in_(ids)).delete(synchronize_session=False)
            db.query(RFPDraftExport).filter(RFPDraftExport.rfp_id.in_(ids)).delete(synchronize_session=False)
            db.query(RFPChunk).filter(RFPChunk.rfp_id.in_(ids)).delete(synchronize_session=False)
            db.query(GenerationJob).filter(GenerationJob.rfp_id.in_(ids)).delete(synchronize_session=False)
            db.query(AuditLog).filter(AuditLog.rfp_id.in_(ids)).delete(synchronize_session=False)
            db.query(RFPDocument).filter(RFPDocument.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
        if args.delete_exports:
            for path in Path("storage/exports").glob("rfp_*_private_short_draft.docx"):
                path.unlink(missing_ok=True)
        print({"deleted_demo_rfps": ids, "exports_deleted": args.delete_exports})
    finally:
        db.close()


if __name__ == "__main__":
    main()
