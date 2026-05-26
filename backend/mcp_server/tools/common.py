from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPChunk, RFPDocument
from app.services.audit_service import log_event

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = (PROJECT_ROOT / "storage" / "exports").resolve()


@contextmanager
def db_session() -> Iterator[Session]:
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def friendly_error(message: str) -> dict[str, Any]:
    return {"error": message, "external_api_used": False}


def get_existing_rfp(db: Session, rfp_id: int) -> RFPDocument | None:
    if rfp_id <= 0:
        return None
    return db.get(RFPDocument, rfp_id)


def chunk_count(db: Session, rfp_id: int) -> int:
    return db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).count()


def validate_top_k(top_k: int) -> int:
    if top_k < 1:
        return 1
    return min(top_k, 10)


def safe_export_path(path_value: str) -> str | None:
    path = Path(path_value).resolve()
    try:
        path.relative_to(EXPORTS_DIR)
    except ValueError:
        return None
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return None


def log_mcp_tool(db: Session, tool_name: str, rfp_id: int | None = None, event_type: str = "mcp_tool_invoked", details: dict | None = None) -> None:
    log_event(
        db,
        event_type=event_type,
        action=tool_name,
        rfp_id=rfp_id,
        source="mcp",
        details=details,
        external_api_used=False,
    )
