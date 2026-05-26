import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.rfp import AuditLog


def log_event(
    db: Session,
    event_type: str,
    action: str,
    rfp_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    source: str = "backend",
    details: dict[str, Any] | None = None,
    external_api_used: bool = False,
) -> AuditLog:
    log = AuditLog(
        event_type=event_type,
        action=action,
        rfp_id=rfp_id,
        entity_type=entity_type,
        entity_id=entity_id,
        source=source,
        details_json=json.dumps(details) if details is not None else None,
        external_api_used=external_api_used,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_audit_logs(db: Session, rfp_id: int | None = None, limit: int = 100) -> list[AuditLog]:
    query = db.query(AuditLog)
    if rfp_id is not None:
        query = query.filter(AuditLog.rfp_id == rfp_id)
    return query.order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 500)).all()
