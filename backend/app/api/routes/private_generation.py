from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rfp import RFPDraftExport, RFPDraftSection
from app.schemas.rfp import RFPDraftSectionResponse
from app.services.docx_export_service import export_private_short_draft
from app.services.draft_quality_service import evaluate_draft_quality
from app.services.draft_validation_service import DraftNotReadyError
from app.services.audit_service import log_event
from app.services.draft_validation_service import get_section_validation_issues, section_contains_invalid_content
from app.services.job_service import get_latest_generation_job, mark_stale_generation_job_if_needed
from app.services.private_generation_service import GenerationAlreadyRunningError, generate_private_short_draft

router = APIRouter(prefix="/private-rfp", tags=["private-generation"])


@router.post("/{rfp_id}/generate-short-draft")
def generate_short_draft(rfp_id: int, confirm_regenerate: bool = False, db: Session = Depends(get_db)) -> dict:
    try:
        return generate_private_short_draft(db, rfp_id, confirm_regenerate=confirm_regenerate)
    except GenerationAlreadyRunningError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": True,
                "code": exc.code,
                "message": str(exc),
                "current_job": exc.current_job,
            },
        )
    except ValueError as exc:
        job = get_latest_generation_job(db, rfp_id)
        if job is not None and job.status == "failed_partial":
            generated_sections = (
                db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp_id).count()
            )
            return {
                "rfp_id": rfp_id,
                "status": "failed_partial",
                "sections_generated": generated_sections,
                "provider": "local_ollama",
                "external_api_used": False,
                "job_id": job.id,
                "error": str(exc),
            }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{rfp_id}/draft", response_model=list[RFPDraftSectionResponse])
def get_short_draft(rfp_id: int, db: Session = Depends(get_db)) -> list[RFPDraftSection]:
    sections = db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp_id).order_by(RFPDraftSection.section_order).all()
    return [
        {
            **RFPDraftSectionResponse.model_validate(section).model_dump(),
            "validation_status": "invalid" if section_contains_invalid_content(section.section_content) else "valid",
            "validation_issues": get_section_validation_issues(section.section_content),
            "has_infrastructure_error": section_contains_invalid_content(section.section_content),
        }
        for section in sections
    ]


@router.get("/{rfp_id}/quality")
def get_draft_quality(rfp_id: int, db: Session = Depends(get_db)) -> dict:
    result = evaluate_draft_quality(db, rfp_id)
    log_event(db, "quality_check_executed", "get_draft_quality", rfp_id=rfp_id, source="frontend", details={"overall_status": result.get("overall_status"), "check_count": len(result.get("checks", []))})
    return result


@router.post("/{rfp_id}/export-docx")
def export_draft_docx(rfp_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        result = export_private_short_draft(db, rfp_id)
        log_event(db, "docx_exported", "export_private_docx", rfp_id=rfp_id, entity_type="RFPDraftExport", entity_id=result.get("export_id"), source="frontend", details={"file_name": result.get("file_name"), "word_count": result.get("word_count")})
        return result
    except DraftNotReadyError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": True, "code": exc.code, "message": str(exc)},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{rfp_id}/download")
def download_latest_draft(rfp_id: int, db: Session = Depends(get_db)) -> FileResponse:
    latest_export = (
        db.query(RFPDraftExport)
        .filter(RFPDraftExport.rfp_id == rfp_id, RFPDraftExport.export_type == "private_short_draft")
        .order_by(RFPDraftExport.created_at.desc())
        .first()
    )
    if latest_export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No DOCX export found for this RFP.")

    path = Path(latest_export.file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file is missing on disk.")
    log_event(db, "docx_downloaded", "download_private_docx", rfp_id=rfp_id, entity_type="RFPDraftExport", entity_id=latest_export.id, source="frontend", details={"file_name": latest_export.file_name})

    return FileResponse(
        path=path,
        filename=latest_export.file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/{rfp_id}/draft/download")
def download_latest_draft_alias(rfp_id: int, db: Session = Depends(get_db)) -> FileResponse:
    return download_latest_draft(rfp_id, db)


@router.get("/{rfp_id}/generation-progress")
def get_generation_progress(rfp_id: int, db: Session = Depends(get_db)) -> dict:
    job = get_latest_generation_job(db, rfp_id)
    if job is None:
        return {
            "rfp_id": rfp_id,
            "job_id": None,
            "status": "not_started",
            "current_step": 0,
            "total_steps": 8,
            "current_section": None,
            "progress_percent": 0,
            "external_api_used": False,
            "started_at": None,
            "updated_at": None,
            "completed_at": None,
            "elapsed_seconds": 0,
            "estimated_total_seconds": None,
            "estimated_remaining_seconds": None,
            "average_seconds_per_section": None,
            "model_used": None,
        }
    previous_status = job.status
    job = mark_stale_generation_job_if_needed(db, job) or job
    if previous_status == "running" and job.status == "failed_stale":
        log_event(
            db,
            "generation_job_marked_stale",
            "generation_progress_check",
            rfp_id=rfp_id,
            entity_type="GenerationJob",
            entity_id=job.id,
            source="backend",
            details={"reason": job.error_message, "status": job.status},
            external_api_used=False,
        )
    return {
        "rfp_id": rfp_id,
        "job_id": job.id,
        "status": job.status,
        "current_step": job.current_step,
        "total_steps": job.total_steps,
        "current_section": job.current_section,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message,
        "external_api_used": job.external_api_used,
        "started_at": job.started_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at,
        "elapsed_seconds": job.elapsed_seconds,
        "estimated_total_seconds": job.estimated_total_seconds,
        "estimated_remaining_seconds": job.estimated_remaining_seconds,
        "average_seconds_per_section": job.average_seconds_per_section,
        "model_used": job.model_used,
    }
