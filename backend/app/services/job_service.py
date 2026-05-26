from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.rfp import GenerationJob

STALE_JOB_MINUTES = 15


def create_generation_job(db: Session, rfp_id: int) -> GenerationJob:
    job = GenerationJob(
        rfp_id=rfp_id,
        status="queued",
        current_step=0,
        total_steps=8,
        progress_percent=0,
        model_used=None,
        external_api_used=False,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_generation_job(
    db: Session,
    job_id: int,
    current_step: int,
    total_steps: int,
    current_section: str,
    status: str = "running",
) -> GenerationJob | None:
    job = db.get(GenerationJob, job_id)
    if job is None:
        return None
    now = datetime.utcnow()
    job.status = status
    job.current_step = current_step
    job.total_steps = total_steps
    job.current_section = current_section
    job.progress_percent = int((current_step / total_steps) * 100) if total_steps else 0
    job.started_at = job.started_at or now
    job.updated_at = now
    elapsed = (now - job.started_at).total_seconds() if job.started_at else 0.0
    completed_sections = max(current_step, 1)
    average = elapsed / completed_sections if elapsed > 0 and completed_sections > 0 else None
    job.elapsed_seconds = round(elapsed, 2) if elapsed else 0.0
    job.average_seconds_per_section = round(average, 2) if average is not None else None
    if average is not None:
        job.estimated_total_seconds = round(average * total_steps, 2)
        remaining = max((total_steps - current_step), 0)
        job.estimated_remaining_seconds = round(average * remaining, 2)
    db.commit()
    db.refresh(job)
    return job


def complete_generation_job(db: Session, job_id: int) -> GenerationJob | None:
    job = db.get(GenerationJob, job_id)
    if job is None:
        return None
    now = datetime.utcnow()
    job.status = "completed"
    job.current_step = job.total_steps
    job.progress_percent = 100
    job.updated_at = now
    job.completed_at = now
    job.elapsed_seconds = (now - job.started_at).total_seconds() if job.started_at else 0.0
    job.external_api_used = False
    db.commit()
    db.refresh(job)
    return job


def fail_generation_job(db: Session, job_id: int, error_message: str) -> GenerationJob | None:
    job = db.get(GenerationJob, job_id)
    if job is None:
        return None
    now = datetime.utcnow()
    job.status = "failed"
    job.error_message = error_message
    job.updated_at = now
    job.completed_at = now
    job.elapsed_seconds = (now - job.started_at).total_seconds() if job.started_at else 0.0
    job.external_api_used = False
    db.commit()
    db.refresh(job)
    return job


def get_latest_generation_job(db: Session, rfp_id: int) -> GenerationJob | None:
    return (
        db.query(GenerationJob)
        .filter(GenerationJob.rfp_id == rfp_id)
        .order_by(GenerationJob.id.desc())
        .first()
    )


def mark_stale_generation_job_if_needed(db: Session, job: GenerationJob, stale_minutes: int = STALE_JOB_MINUTES) -> GenerationJob | None:
    if job.status != "running":
        return job

    now = datetime.utcnow()
    reference_time = job.updated_at or job.started_at
    if reference_time is None:
        if job.current_step == 0 and job.progress_percent == 0:
            return _mark_stale_job(db, job, now)
        return job

    if now - reference_time < timedelta(minutes=stale_minutes):
        return job

    if job.current_step == 0 and job.progress_percent == 0:
        return _mark_stale_job(db, job, now)

    return _mark_stale_job(db, job, now)


def _mark_stale_job(db: Session, job: GenerationJob, now: datetime) -> GenerationJob:
    job.status = "failed_stale"
    job.error_message = "Generation was interrupted or stale after laptop restart."
    job.updated_at = now
    job.completed_at = now
    job.elapsed_seconds = (now - job.started_at).total_seconds() if job.started_at else 0.0
    job.external_api_used = False
    db.commit()
    db.refresh(job)
    return job
