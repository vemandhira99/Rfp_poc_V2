import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument, RFPDraftSection
from app.services.private_generation_service import generate_private_short_draft


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        rfp = (
            db.query(RFPDocument)
            .filter(RFPDocument.status == "ready_for_private_chat")
            .order_by(RFPDocument.created_at.desc())
            .first()
        )
        if rfp is None:
            print("No ready RFP found. Upload a valid or limited-but-valid RFP first.")
            return

        result = generate_private_short_draft(db, rfp.id)
        sections = db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp.id).all()
        print(result)
        print("Section count:", len(sections))
        print("External API used:", result["external_api_used"])
        print("Has 8 sections:", len(sections) == 8)
    finally:
        db.close()


if __name__ == "__main__":
    main()
