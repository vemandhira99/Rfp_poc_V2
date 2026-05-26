from typing import Any

from app.models.rfp import RFPDraftExport
from app.services.docx_export_service import export_private_short_draft
from app.services.private_generation_service import generate_private_short_draft
from mcp_server.tools.common import db_session, friendly_error, get_existing_rfp, log_mcp_tool, safe_export_path


def generate_private_short_draft_tool(rfp_id: int, confirm: bool = False, confirm_regenerate: bool = False) -> dict[str, Any]:
    if confirm is not True:
        return friendly_error("Confirmation required before running local draft generation.")
    with db_session() as db:
        log_mcp_tool(db, "generate_private_short_draft", rfp_id=rfp_id, event_type="mcp_generate_private_short_draft")
        if get_existing_rfp(db, rfp_id) is None:
            return friendly_error("RFP document not found.")
        try:
            return generate_private_short_draft(db, rfp_id, confirm_regenerate=confirm_regenerate)
        except ValueError as exc:
            return friendly_error(str(exc))


def export_private_docx_tool(rfp_id: int) -> dict[str, Any]:
    with db_session() as db:
        log_mcp_tool(db, "export_private_docx", rfp_id=rfp_id, event_type="mcp_export_private_docx")
        if get_existing_rfp(db, rfp_id) is None:
            return friendly_error("RFP document not found.")
        try:
            result = export_private_short_draft(db, rfp_id)
        except ValueError as exc:
            return friendly_error(str(exc))

        safe_path = safe_export_path(result["file_path"])
        if safe_path is None:
            return friendly_error("Export path failed local storage validation.")
        return {
            "file_path": safe_path,
            "file_name": result["file_name"],
            "external_api_used": False,
        }


def latest_export_metadata(rfp_id: int) -> dict[str, Any]:
    with db_session() as db:
        export = (
            db.query(RFPDraftExport)
            .filter(RFPDraftExport.rfp_id == rfp_id, RFPDraftExport.export_type == "private_short_draft")
            .order_by(RFPDraftExport.created_at.desc())
            .first()
        )
        if export is None:
            return friendly_error("No export found.")
        safe_path = safe_export_path(export.file_path)
        if safe_path is None:
            return friendly_error("Export path failed local storage validation.")
        return {"file_path": safe_path, "file_name": export.file_name, "external_api_used": False}
