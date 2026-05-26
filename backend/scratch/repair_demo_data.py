from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import GenerationJob, RFPDocument, RFPDraftExport, RFPDraftSection
from app.services.audit_service import log_event
from app.services.draft_validation_service import section_contains_invalid_content


BACKEND_ROOT = Path(__file__).resolve().parents[1]
EXPORTS_DIR = (BACKEND_ROOT / "storage" / "exports").resolve()
STALE_JOB_AGE = timedelta(minutes=15)
INVALID_MARKERS = [
    "ollama is not running",
    "please start ollama",
    "model is not available",
    "connection refused",
    "traceback",
    "exception",
]


def main() -> None:
    init_db()
    repaired_rfps = 0
    invalid_sections_removed = 0
    stale_jobs_marked_failed = 0
    audit_events_created = 0
    now = datetime.utcnow()

    with SessionLocal() as db:
        affected_rfp_ids = sorted(
            {
                section.rfp_id
                for section in db.query(RFPDraftSection).all()
                if section_contains_invalid_content(section.section_content or "")
            }
        )

        for rfp_id in affected_rfp_ids:
            rfp = db.get(RFPDocument, rfp_id)
            if rfp is None:
                continue

            sections = (
                db.query(RFPDraftSection)
                .filter(RFPDraftSection.rfp_id == rfp_id)
                .order_by(RFPDraftSection.section_order)
                .all()
            )
            invalid_sections = [section for section in sections if section_contains_invalid_content(section.section_content or "")]
            if not invalid_sections:
                continue

            invalid_sections_removed += len(invalid_sections)
            for section in invalid_sections:
                db.delete(section)

            exports = (
                db.query(RFPDraftExport)
                .filter(RFPDraftExport.rfp_id == rfp_id, RFPDraftExport.export_type == "private_short_draft")
                .all()
            )
            for export in exports:
                file_path = Path(export.file_path)
                if not file_path.is_absolute():
                    file_path = (BACKEND_ROOT / file_path).resolve()
                try:
                    file_path.relative_to(EXPORTS_DIR)
                except ValueError:
                    pass
                else:
                    if file_path.exists():
                        file_path.unlink()
                db.delete(export)

            if rfp.status == "draft_generated" or invalid_sections:
                rfp.status = "ready_for_private_chat"
                repaired_rfps += 1

            db.commit()
            log_event(
                db,
                event_type="invalid_demo_draft_repaired",
                action="repair_demo_draft",
                rfp_id=rfp_id,
                entity_type="RFPDocument",
                entity_id=rfp.id,
                source="backend",
                details={
                    "removed_sections": len(invalid_sections),
                    "removed_exports": len(exports),
                    "remaining_sections": db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp_id).count(),
                },
                external_api_used=False,
            )
            audit_events_created += 1
            db.commit()

        stale_jobs = db.query(GenerationJob).filter(GenerationJob.status == "running").all()
        for job in stale_jobs:
            reference_time = job.updated_at or job.started_at
            age = now - reference_time if reference_time is not None else STALE_JOB_AGE + timedelta(seconds=1)
            is_stale = age > STALE_JOB_AGE or (job.current_step == 0 and job.progress_percent == 0)
            if not is_stale:
                continue

            job.status = "failed_stale"
            job.error_message = "Generation was interrupted or stale after laptop restart."
            job.completed_at = now
            job.updated_at = now
            job.external_api_used = False
            job.elapsed_seconds = (now - job.started_at).total_seconds() if job.started_at else 0.0
            stale_jobs_marked_failed += 1
            db.commit()
            log_event(
                db,
                event_type="generation_job_marked_stale",
                action="repair_stale_generation_job",
                rfp_id=job.rfp_id,
                entity_type="GenerationJob",
                entity_id=job.id,
                source="backend",
                details={"status": job.status, "error_message": job.error_message},
                external_api_used=False,
            )
            audit_events_created += 1
            db.commit()

    print("repair_demo_data summary")
    print(f"repaired_rfps={repaired_rfps}")
    print(f"invalid_sections_removed={invalid_sections_removed}")
    print(f"stale_jobs_marked_failed={stale_jobs_marked_failed}")
    print(f"audit_events_created={audit_events_created}")


if __name__ == "__main__":
    main()
