from mcp.server.fastmcp import FastMCP

from mcp_server.tools.chat_tools import ask_private_rfp_tool
from mcp_server.tools.generation_tools import export_private_docx_tool, generate_private_short_draft_tool
from mcp_server.tools.quality_tools import get_draft_quality_tool
from mcp_server.tools.retrieval_tools import search_rfp_chunks_tool
from mcp_server.tools.rfp_tools import get_rfp_metadata_tool, list_rfps_tool

mcp = FastMCP("Private RFP Tool MCP")


@mcp.tool()
def list_rfps() -> list[dict]:
    return list_rfps_tool()


@mcp.tool()
def get_rfp_metadata(rfp_id: int) -> dict:
    return get_rfp_metadata_tool(rfp_id)


@mcp.tool()
def search_rfp_chunks(rfp_id: int, query: str, top_k: int = 5) -> dict:
    return search_rfp_chunks_tool(rfp_id, query, top_k)


@mcp.tool()
def ask_private_rfp(rfp_id: int, question: str) -> dict:
    return ask_private_rfp_tool(rfp_id, question)


@mcp.tool()
def generate_private_short_draft(rfp_id: int, confirm: bool = False, confirm_regenerate: bool = False) -> dict:
    return generate_private_short_draft_tool(rfp_id, confirm=confirm, confirm_regenerate=confirm_regenerate)


@mcp.tool()
def get_draft_quality(rfp_id: int) -> dict:
    return get_draft_quality_tool(rfp_id)


@mcp.tool()
def export_private_docx(rfp_id: int) -> dict:
    return export_private_docx_tool(rfp_id)


if __name__ == "__main__":
    mcp.run()
