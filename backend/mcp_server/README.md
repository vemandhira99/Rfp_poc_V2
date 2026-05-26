# Private RFP Tool MCP Server

This MCP server is for local development only. It wraps existing Private RFP Tool backend services and exposes a small, controlled set of tools to MCP-compatible clients.

## Security Position

- Local-only MCP server.
- No public network hosting.
- No shell command execution.
- No arbitrary filesystem browsing.
- No database delete/update tools.
- No secret access tools.
- No Gemini, Azure, OpenAI, Claude, or external AI provider calls.
- No autonomous workflow execution.
- DOCX export paths are limited to `backend/storage/exports`.

The generation tools call only the existing local Ollama-backed services.

## Install

From `backend`:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

## Start

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m mcp_server.server
```

This uses the Python MCP SDK `FastMCP` server entrypoint. Keep it local and connect only trusted local MCP clients.

## Tools

### list_rfps

Lists uploaded RFP metadata:

- `id`
- `title`
- `original_filename`
- `document_quality`
- `status`
- `word_count`
- `chunk_count`

### get_rfp_metadata

Input:

- `rfp_id`

Returns document metadata and classification details.

### search_rfp_chunks

Input:

- `rfp_id`
- `query`
- `top_k`, capped at 10

Uses existing hybrid retrieval and returns safe previews only.

### ask_private_rfp

Input:

- `rfp_id`
- `question`

Uses existing private chat service. Returns answer, provider, model, `external_api_used=false`, and source chunks.

### generate_private_short_draft

Input:

- `rfp_id`
- `confirm`

Generates the controlled eight-section private short draft using the local Ollama model. This writes draft section rows, but does not delete or modify source RFP data.

`confirm` must be `true`. If omitted or false, the tool returns a confirmation-required error.

### get_draft_quality

Input:

- `rfp_id`

Returns deterministic quality checks.

### export_private_docx

Input:

- `rfp_id`

Exports the generated draft to DOCX under `backend/storage/exports`.

## Basic Validation

Run without an MCP client:

```powershell
.\.venv\Scripts\python.exe -B scratch\test_mcp_tools.py
```

This imports the tool functions directly and validates list, metadata, retrieval, and private chat behavior.

To validate the confirmation guard:

```powershell
.\.venv\Scripts\python.exe -B scratch\test_mcp_confirm.py
```
