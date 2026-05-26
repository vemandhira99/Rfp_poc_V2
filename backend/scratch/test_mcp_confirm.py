import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcp_server.tools.generation_tools import generate_private_short_draft_tool
from mcp_server.tools.rfp_tools import list_rfps_tool


def main() -> None:
    rfps = list_rfps_tool()
    if not rfps:
        print("No RFPs found.")
        return
    rfp_id = int(rfps[0]["id"])
    without_confirm = generate_private_short_draft_tool(rfp_id, confirm=False)
    print("Without confirm:", without_confirm)
    print("Confirmation required:", "Confirmation required" in without_confirm.get("error", ""))
    print("With confirm skipped by default to avoid long local generation.")


if __name__ == "__main__":
    main()
