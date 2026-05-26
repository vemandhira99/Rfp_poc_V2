# Private RFP Tool Final Architecture

## Overview

Browser -> Next.js frontend -> FastAPI backend -> SQLite / local storage / Ollama

MCP client -> local MCP server -> existing backend services -> SQLite / Ollama

## Core Services

- Upload and parsing service
- Deterministic classification service
- Metadata extraction service
- Chunking and local embeddings service
- Hybrid retrieval service
- Private chat service
- Private draft generation service
- DOCX export service
- Audit service
- Usage service
- Shared Ollama health service

## Shared Ollama Health

All runtime checks use one source of truth:

- backend availability
- chat model availability
- embedding model availability

The UI badge, chat, embeddings, generation, and export all use that same check.

## Draft Safety Rules

- Generation refuses to start when Ollama is unavailable.
- Error text is rejected before it can be saved as draft content.
- Export validates that 8 sections exist and the generation job completed.
- Failed or partial jobs never become valid DOCX output.

## Progress And Metrics

- Generation jobs track current section, progress, elapsed time, and ETA.
- Local usage logs track prompt words, response words, estimated tokens, elapsed seconds, and retrieval chunks used.
- `external_api_used` is always false in private mode.

## UI Shape

- Calm dashboard
- Guided workflow stepper
- Collapsible sidebar
- Premium status cards
- Draft progress timeline
- Simple local settings panel

## Security Posture

- Local-only runtime
- No external AI provider code paths in private mode
- Audit logs retained for proof
- MCP generation requires confirmation

