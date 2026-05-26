import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.rfp import RFPDocument
from app.schemas.rfp import UploadRFPResponse
from app.services.chunking_service import create_chunks_for_rfp
from app.services.audit_service import log_event
from app.services.classification_service import classify_document
from app.services.metadata_extraction_service import extract_probable_metadata
from app.services.parsing_service import SUPPORTED_EXTENSIONS, extract_text_from_file

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/rfp", response_model=UploadRFPResponse)
def upload_rfp(file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadRFPResponse:
    original_filename = file.filename or "uploaded_rfp"
    extension = Path(original_filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supported file types are PDF, DOCX, and TXT.")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{extension}"
    destination = upload_dir / stored_filename

    file_size = _save_upload(file, destination)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if file_size > max_bytes:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Upload exceeds {settings.MAX_UPLOAD_MB} MB.")

    rfp = RFPDocument(
        title=Path(original_filename).stem,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(destination),
        file_type=extension.lstrip("."),
        file_size=file_size,
    )
    db.add(rfp)
    db.commit()
    db.refresh(rfp)
    log_event(
        db,
        event_type="rfp_uploaded",
        action="upload_rfp",
        rfp_id=rfp.id,
        entity_type="RFPDocument",
        entity_id=rfp.id,
        source="frontend",
        details={"filename": original_filename, "file_size": file_size},
    )

    try:
        parsed = extract_text_from_file(str(destination))
        metadata = extract_probable_metadata(str(parsed["text"]), original_filename)
        chunk_count = 0
        classification = classify_document(
            page_count=int(parsed["page_count"]),
            word_count=int(parsed["word_count"]),
            character_count=int(parsed["character_count"]),
            text=str(parsed["text"]),
        )
        rfp.page_count = int(parsed["page_count"])
        rfp.word_count = int(parsed["word_count"])
        rfp.character_count = int(parsed["character_count"])
        rfp.line_count = int(parsed["line_count"])
        rfp.extracted_text = str(parsed["text"])
        rfp.probable_title = metadata["probable_title"]
        rfp.probable_client = metadata["probable_client"]
        rfp.probable_deadline = metadata["probable_deadline"]
        rfp.probable_submission_date = metadata["probable_submission_date"]
        rfp.document_quality = classification["document_quality"]
        rfp.classification_reason = classification["reason"]
        rfp.status = classification["status"]
        db.commit()
        db.refresh(rfp)
        log_event(
            db,
            event_type="rfp_classified",
            action="classify_rfp",
            rfp_id=rfp.id,
            entity_type="RFPDocument",
            entity_id=rfp.id,
            source="backend",
            details={
                "document_quality": rfp.document_quality,
                "status": rfp.status,
                "word_count": rfp.word_count,
                "chunk_count": chunk_count if "chunk_count" in locals() else 0,
                "classification_reason": rfp.classification_reason,
            },
        )

        if rfp.document_quality in {"valid_rfp", "limited_but_valid"}:
            chunk_count = create_chunks_for_rfp(db, rfp.id, rfp.extracted_text or "")
    except Exception as exc:
        rfp.status = "parse_failed"
        rfp.classification_reason = str(exc)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse uploaded document: {exc}") from exc

    return UploadRFPResponse(
        rfp_id=rfp.id,
        original_filename=rfp.original_filename,
        stored_filename=rfp.stored_filename,
        file_type=rfp.file_type,
        file_size=rfp.file_size,
        page_count=rfp.page_count,
        word_count=rfp.word_count,
        character_count=rfp.character_count,
        line_count=rfp.line_count,
        extracted_text_preview=(rfp.extracted_text or "")[:500] if rfp.extracted_text else None,
        probable_title=rfp.probable_title,
        probable_client=rfp.probable_client,
        probable_deadline=rfp.probable_deadline,
        probable_submission_date=rfp.probable_submission_date,
        document_quality=rfp.document_quality,
        status=rfp.status,
        reason=rfp.classification_reason or "",
        chunk_count=chunk_count,
        external_api_used=False,
    )


def _save_upload(file: UploadFile, destination: Path) -> int:
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return destination.stat().st_size
