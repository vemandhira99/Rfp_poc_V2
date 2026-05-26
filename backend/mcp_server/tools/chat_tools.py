from typing import Any

from app.services.private_chat_service import answer_private_rfp_question
from mcp_server.tools.common import db_session, friendly_error, get_existing_rfp, log_mcp_tool


def ask_private_rfp_tool(rfp_id: int, question: str) -> dict[str, Any]:
    if not question.strip():
        return friendly_error("Question is required.")
    with db_session() as db:
        log_mcp_tool(db, "ask_private_rfp", rfp_id=rfp_id, details={"question_length": len(question)})
        if get_existing_rfp(db, rfp_id) is None:
            return friendly_error("RFP document not found.")
        try:
            result = answer_private_rfp_question(db, rfp_id, question)
        except ValueError as exc:
            return friendly_error(str(exc))
        return {
            "answer": result.get("answer"),
            "provider": result.get("provider"),
            "model_used": result.get("model_used"),
            "retrieval_mode": result.get("retrieval_mode"),
            "external_api_used": False,
            "source_chunks": result.get("source_chunks", []),
        }
