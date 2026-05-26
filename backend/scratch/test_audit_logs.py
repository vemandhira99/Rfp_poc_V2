import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services.audit_service import list_audit_logs, log_event


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        rfp = db.query(RFPDocument).order_by(RFPDocument.created_at.desc()).first()
        if rfp:
            log_event(db, "validation_audit_test", "test_audit_logs", rfp_id=rfp.id, source="system")
            logs = list_audit_logs(db, rfp_id=rfp.id, limit=10)
        else:
            log_event(db, "validation_audit_test", "test_audit_logs", source="system")
            logs = list_audit_logs(db, limit=10)
        print("Audit log count:", len(logs))
        print("Latest:", {"event_type": logs[0].event_type, "external_api_used": logs[0].external_api_used} if logs else None)
    finally:
        db.close()


if __name__ == "__main__":
    main()
