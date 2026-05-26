import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcp_server.tools.chat_tools import ask_private_rfp_tool
from mcp_server.tools.quality_tools import get_draft_quality_tool
from mcp_server.tools.retrieval_tools import search_rfp_chunks_tool
from mcp_server.tools.rfp_tools import get_rfp_metadata_tool, list_rfps_tool


def main() -> None:
    rfps = list_rfps_tool()
    print("RFP count:", len(rfps))
    if not rfps:
        print("No RFPs found. Upload an RFP first.")
        return

    rfp_id = int(rfps[0]["id"])
    print("Latest RFP:", rfps[0])

    metadata = get_rfp_metadata_tool(rfp_id)
    print("Metadata:", metadata)

    retrieval = search_rfp_chunks_tool(rfp_id, "scope requirements deadline", top_k=5)
    print("Retrieval result count:", len(retrieval.get("results", [])))
    print("Top retrieval type:", retrieval.get("results", [{}])[0].get("retrieval_type") if retrieval.get("results") else "none")

    chat = ask_private_rfp_tool(rfp_id, "What is this RFP about?")
    print("Chat provider:", chat.get("provider"))
    print("External API used:", chat.get("external_api_used"))

    quality = get_draft_quality_tool(rfp_id)
    print("Quality status:", quality.get("overall_status"))


if __name__ == "__main__":
    main()
