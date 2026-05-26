import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services.docx_export_service import export_private_short_draft


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
            print("No ready RFP found.")
            return

        result = export_private_short_draft(db, rfp.id)
        path = Path(result["file_path"])
        print(result)
        print("File exists:", path.exists())
        print("File size > 0:", path.exists() and path.stat().st_size > 0)
    finally:
        db.close()


if __name__ == "__main__":
    main()
