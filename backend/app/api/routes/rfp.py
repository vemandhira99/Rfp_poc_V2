from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rfp import RFPChunk, RFPDocument
from app.schemas.rfp import RFPChunkResponse, RFPDocumentDetail, RFPDocumentSummary
from app.services.audit_service import log_event
from app.services.job_service import get_latest_generation_job, mark_stale_generation_job_if_needed
from app.services.local_embedding_service import embed_chunks_for_rfp
from app.services.metadata_extraction_service import extract_probable_metadata
from app.services.retrieval_service import search_chunks

router = APIRouter(prefix="/rfps", tags=["rfps"])


@router.get("", response_model=list[RFPDocumentSummary])
def list_rfps(db: Session = Depends(get_db)) -> list[RFPDocument]:
    rfps = db.query(RFPDocument).order_by(RFPDocument.created_at.desc()).all()
    for rfp in rfps:
        _attach_document_context(rfp)
        _attach_generation_context(db, rfp)
        _attach_embedding_summary(db, rfp)
    return rfps


@router.get("/{rfp_id}", response_model=RFPDocumentDetail)
def get_rfp(rfp_id: int, db: Session = Depends(get_db)) -> RFPDocument:
    rfp = db.get(RFPDocument, rfp_id)
    if rfp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFP document not found.")
    _attach_document_context(rfp)
    _attach_generation_context(db, rfp)
    _attach_embedding_summary(db, rfp)
    return rfp


@router.post("/{rfp_id}/refresh-metadata", response_model=RFPDocumentDetail)
def refresh_metadata(rfp_id: int, db: Session = Depends(get_db)) -> RFPDocument:
    rfp = db.get(RFPDocument, rfp_id)
    if rfp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFP document not found.")
    if not rfp.extracted_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No extracted text is available for metadata refresh.")

    metadata = extract_probable_metadata(rfp.extracted_text, rfp.original_filename)
    rfp.probable_title = metadata["probable_title"]
    rfp.probable_client = metadata["probable_client"]
    rfp.probable_deadline = metadata["probable_deadline"]
    rfp.probable_submission_date = metadata["probable_submission_date"]
    db.commit()
    db.refresh(rfp)
    _attach_document_context(rfp)
    _attach_generation_context(db, rfp)
    _attach_embedding_summary(db, rfp)
    log_event(
        db,
        event_type="rfp_metadata_refreshed",
        action="refresh_metadata",
        rfp_id=rfp_id,
        entity_type="RFPDocument",
        entity_id=rfp_id,
        source="backend",
        details={
            "probable_title": rfp.probable_title,
            "probable_client": rfp.probable_client,
            "probable_deadline": rfp.probable_deadline,
            "probable_submission_date": rfp.probable_submission_date,
            "metadata_confidence": getattr(rfp, "metadata_confidence", None),
        },
    )
    return rfp


@router.post("/{rfp_id}/embed")
def embed_rfp_chunks(rfp_id: int, db: Session = Depends(get_db)) -> dict:
    rfp = db.get(RFPDocument, rfp_id)
    if rfp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFP document not found.")

    chunk_count = db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).count()
    embedded_count = (
        db.query(RFPChunk)
        .filter(RFPChunk.rfp_id == rfp_id, RFPChunk.embedding_status == "completed", RFPChunk.embedding_json.isnot(None))
        .count()
    )
    if chunk_count > 0 and embedded_count == chunk_count:
        return {
            "rfp_id": rfp_id,
            "embedding_status": "completed",
            "embedded_chunks": embedded_count,
            "failed_chunks": 0,
            "external_api_used": False,
            "already_prepared": True,
        }

    try:
        result = embed_chunks_for_rfp(db, rfp_id)
        embedding_status = "completed" if result["failed_chunks"] == 0 else "partial"
        log_event(
            db,
            event_type="embeddings_generated",
            action="embed_rfp_chunks",
            rfp_id=rfp_id,
            entity_type="RFPDocument",
            entity_id=rfp_id,
            source="backend",
            details=result,
        )
        return {
            "rfp_id": rfp_id,
            "embedding_status": embedding_status,
            "embedded_chunks": result["embedded_chunks"],
            "failed_chunks": result["failed_chunks"],
            "external_api_used": False,
            "already_prepared": False,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{rfp_id}/retrieval-test")
def test_retrieval(rfp_id: int, q: str, mode: str = "hybrid", db: Session = Depends(get_db)) -> dict:
    if db.get(RFPDocument, rfp_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFP document not found.")
    results = search_chunks(db, rfp_id, q, top_k=5, mode=mode)
    log_event(
        db,
        event_type="retrieval_test_executed",
        action="retrieval_test",
        rfp_id=rfp_id,
        source="backend",
        details={"query": q, "mode": mode, "result_count": len(results)},
    )
    return {"query": q, "mode": mode, "results": results}


@router.get("/{rfp_id}/chunks", response_model=list[RFPChunkResponse])
def get_rfp_chunks(rfp_id: int, db: Session = Depends(get_db)) -> list[RFPChunk]:
    if db.get(RFPDocument, rfp_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFP document not found.")
    return db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).order_by(RFPChunk.chunk_order).all()


def _attach_embedding_summary(db: Session, rfp: RFPDocument) -> None:
    chunk_count = db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp.id).count()
    embedded_count = (
        db.query(RFPChunk)
        .filter(RFPChunk.rfp_id == rfp.id, RFPChunk.embedding_status == "completed", RFPChunk.embedding_json.isnot(None))
        .count()
    )
    rfp.chunk_count = chunk_count
    rfp.embedded_chunk_count = embedded_count
    if chunk_count == 0:
        rfp.embedding_status = "not_applicable"
    elif embedded_count == 0:
        rfp.embedding_status = "not_started"
    elif embedded_count == chunk_count:
        rfp.embedding_status = "completed"
    else:
        rfp.embedding_status = "partial"


def _attach_document_context(rfp: RFPDocument) -> None:
    extracted_text = rfp.extracted_text or ""
    if extracted_text.strip():
        metadata = extract_probable_metadata(extracted_text, rfp.original_filename)
        if metadata.get("probable_title"):
            rfp.probable_title = str(metadata["probable_title"])
        if metadata.get("probable_client"):
            rfp.probable_client = str(metadata["probable_client"])
        if metadata.get("probable_deadline"):
            rfp.probable_deadline = str(metadata["probable_deadline"])
        if metadata.get("probable_submission_date"):
            rfp.probable_submission_date = str(metadata["probable_submission_date"])
        rfp.metadata_confidence = metadata.get("metadata_confidence")
        rfp.metadata_reason = metadata.get("metadata_reason")
        rfp.metadata_source_snippet = metadata.get("metadata_source_snippet")


def _attach_generation_context(db: Session, rfp: RFPDocument) -> None:
    job = get_latest_generation_job(db, rfp.id)
    if job is None:
        rfp.generation_job_id = None
        rfp.generation_status = None
        rfp.generation_current_section = None
        rfp.generation_progress_percent = None
        rfp.generation_updated_at = None
        rfp.generation_started_at = None
        return
    job = mark_stale_generation_job_if_needed(db, job) or job
    rfp.generation_job_id = job.id
    rfp.generation_status = job.status
    rfp.generation_current_section = job.current_section
    rfp.generation_progress_percent = job.progress_percent
    rfp.generation_updated_at = job.updated_at
    rfp.generation_started_at = job.started_at
