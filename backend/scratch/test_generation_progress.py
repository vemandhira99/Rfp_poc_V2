import sys
import threading
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services.private_generation_service import generate_private_short_draft
from app.services.job_service import get_latest_generation_job


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        rfp = db.query(RFPDocument).filter(RFPDocument.status.in_(["ready_for_private_chat", "draft_generated"])).order_by(RFPDocument.created_at.desc()).first()
        if rfp is None:
            print("No valid RFP found.")
            return
        rfp_id = rfp.id
    finally:
        db.close()

    def run_generation() -> None:
        worker_db = SessionLocal()
        try:
            print(generate_private_short_draft(worker_db, rfp_id))
        finally:
            worker_db.close()

    thread = threading.Thread(target=run_generation, daemon=True)
    thread.start()

    while thread.is_alive():
        db = SessionLocal()
        try:
            job = get_latest_generation_job(db, rfp_id)
            if job:
                print({"status": job.status, "step": job.current_step, "total": job.total_steps, "percent": job.progress_percent, "section": job.current_section})
        finally:
            db.close()
        time.sleep(5)

    db = SessionLocal()
    try:
        job = get_latest_generation_job(db, rfp_id)
        print("Final job:", None if job is None else {"status": job.status, "progress_percent": job.progress_percent, "external_api_used": job.external_api_used})
    finally:
        db.close()


if __name__ == "__main__":
    main()
