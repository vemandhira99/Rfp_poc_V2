from typing import Any

from app.services.retrieval_service import search_chunks
from mcp_server.tools.common import db_session, friendly_error, get_existing_rfp, log_mcp_tool, validate_top_k


def search_rfp_chunks_tool(rfp_id: int, query: str, top_k: int = 5) -> dict[str, Any]:
    if not query.strip():
        return friendly_error("Query is required.")
    safe_top_k = validate_top_k(top_k)
    with db_session() as db:
        log_mcp_tool(db, "search_rfp_chunks", rfp_id=rfp_id, details={"query": query, "top_k": safe_top_k})
        if get_existing_rfp(db, rfp_id) is None:
            return friendly_error("RFP document not found.")
        results = search_chunks(db, rfp_id, query, top_k=safe_top_k, mode="hybrid")
        return {
            "rfp_id": rfp_id,
            "query": query,
            "top_k": safe_top_k,
            "results": [
                {
                    "chunk_id": result["chunk_id"],
                    "chunk_order": result["chunk_order"],
                    "score": result["score"],
                    "retrieval_type": result.get("retrieval_type"),
                    "preview": result.get("preview"),
                }
                for result in results
            ],
            "external_api_used": False,
        }
