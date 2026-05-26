from typing import Any

from app.models.rfp import RFPDocument
from mcp_server.tools.common import chunk_count, db_session, friendly_error, get_existing_rfp, log_mcp_tool


def list_rfps_tool() -> list[dict[str, Any]]:
    with db_session() as db:
        log_mcp_tool(db, "list_rfps")
        rfps = db.query(RFPDocument).order_by(RFPDocument.created_at.desc()).all()
        return [
            {
                "id": rfp.id,
                "title": rfp.title,
                "original_filename": rfp.original_filename,
                "document_quality": rfp.document_quality,
                "status": rfp.status,
                "word_count": rfp.word_count,
                "chunk_count": chunk_count(db, rfp.id),
            }
            for rfp in rfps
        ]


def get_rfp_metadata_tool(rfp_id: int) -> dict[str, Any]:
    with db_session() as db:
        log_mcp_tool(db, "get_rfp_metadata", rfp_id=rfp_id)
        rfp = get_existing_rfp(db, rfp_id)
        if rfp is None:
            return friendly_error("RFP document not found.")
        return {
            "id": rfp.id,
            "title": rfp.title,
            "filename": rfp.original_filename,
            "status": rfp.status,
            "document_quality": rfp.document_quality,
            "page_count": rfp.page_count,
            "word_count": rfp.word_count,
            "character_count": rfp.character_count,
            "classification_reason": rfp.classification_reason,
            "chunk_count": chunk_count(db, rfp.id),
        }
