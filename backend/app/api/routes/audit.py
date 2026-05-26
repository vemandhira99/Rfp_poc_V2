import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.audit_service import list_audit_logs

router = APIRouter(tags=["audit"])


@router.get("/audit/logs")
def get_audit_logs(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    return [_serialize_log(log) for log in list_audit_logs(db, limit=limit)]


@router.get("/audit/export")
def export_audit_logs(rfp_id: int | None = None, limit: int = 500, db: Session = Depends(get_db)) -> StreamingResponse:
    logs = list_audit_logs(db, rfp_id=rfp_id, limit=limit)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "event_type", "rfp_id", "action", "actor", "source", "external_api_used", "created_at", "details_json"])
    for log in logs:
        writer.writerow([log.id, log.event_type, log.rfp_id, log.action, log.actor, log.source, log.external_api_used, log.created_at.isoformat(), log.details_json or ""])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get("/rfps/{rfp_id}/audit")
def get_rfp_audit_logs(rfp_id: int, limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    return [_serialize_log(log) for log in list_audit_logs(db, rfp_id=rfp_id, limit=limit)]


def _serialize_log(log) -> dict:
    return {
        "id": log.id,
        "event_type": log.event_type,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "rfp_id": log.rfp_id,
        "action": log.action,
        "actor": log.actor,
        "source": log.source,
        "details_json": log.details_json,
        "external_api_used": log.external_api_used,
        "created_at": log.created_at,
    }
