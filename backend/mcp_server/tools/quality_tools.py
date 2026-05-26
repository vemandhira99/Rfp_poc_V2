from typing import Any

from app.services.draft_quality_service import evaluate_draft_quality
from mcp_server.tools.common import db_session, friendly_error, get_existing_rfp, log_mcp_tool


def get_draft_quality_tool(rfp_id: int) -> dict[str, Any]:
    with db_session() as db:
        log_mcp_tool(db, "get_draft_quality", rfp_id=rfp_id)
        if get_existing_rfp(db, rfp_id) is None:
            return friendly_error("RFP document not found.")
        result = evaluate_draft_quality(db, rfp_id)
        result["external_api_used"] = False
        return result
