# Private RFP Tool Architecture

## Private Mode

The MVP runs in `AI_MODE=private`. No external AI provider settings are present, and no Gemini, Azure, OpenAI, Claude, MCP, or LangGraph code is included. Uploaded RFP content remains on the local machine.

## Local Parsing

The backend extracts text locally from PDF, DOCX, and TXT files:

- PDF: PyMuPDF
- DOCX: python-docx
- TXT: local file read

OCR is not included in this phase. Scanned or image-based PDFs are detected through deterministic quality checks when they have pages but little extractable text.

## Local Classification

Document quality is classified with deterministic rules based on page count and word count. This avoids model calls during upload and keeps ingestion fast on ordinary Windows laptops.

## Local Retrieval

The first MVP uses lexical retrieval over stored chunks. It lowercases the query, splits terms, scores overlap, and adds a phrase boost. No vector database or embedding pipeline is used yet.

## Phase 2C Local Embeddings

Phase 2C adds optional semantic retrieval using Ollama embeddings with `nomic-embed-text`. Embeddings are generated locally through the configured Ollama base URL and stored directly on `RFPChunk` rows as JSON text.

The chunk fields are:

- `embedding_json`
- `embedding_model`
- `embedding_status`

This avoids pgvector, ChromaDB, and background indexing services for the current Windows laptop target. Cosine similarity is computed in Python over stored JSON vectors, which is simple and measurable for the MVP scale.

Private chat uses hybrid retrieval by default. It tries vector retrieval first when embeddings exist, merges lexical matches, and falls back to lexical retrieval if embeddings are missing or Ollama embeddings fail.

## Phase 2D Private Short Draft Generation

Phase 2D adds controlled local draft generation. The backend generates eight fixed sections:

1. Executive Summary
2. Understanding of RFP
3. Proposed Solution Approach
4. Functional and Technical Coverage
5. Security and Compliance Approach
6. Implementation Plan
7. Risk and Mitigation
8. Conclusion and Next Steps

Each section is generated one at a time using local hybrid retrieval over chunks and the local Ollama chat model. The full RFP is never placed into the prompt. Prompts are kept small with at most five retrieved chunks per section, and output is capped by post-processing to 900 words per section.

Draft sections are stored in `rfp_draft_sections`. DOCX export records are stored in `rfp_draft_exports`, and files are saved under `storage/exports`.

The DOCX export includes a title page, privacy note, table of contents placeholder, the eight sections, and a quality report appendix. The privacy note states that the document was generated locally and no external AI provider was used.

Quality checks are deterministic and flag missing sections, empty sections, duplicate headings, markdown artifacts, overlong sections, and unsupported strong claim keywords. The overall status is always `needs_human_review` for this MVP.

## Phase 2G Safety, Audit, And Progress

Phase 2G adds local audit logging and lightweight generation job tracking without changing the private AI architecture.

Audit logs are stored in `audit_logs` and record important local actions such as upload, classification, embedding generation, retrieval tests, private chat, draft generation, quality checks, DOCX export/download, and MCP tool invocation. Audit events include `external_api_used=false`.

Draft generation jobs are stored in `generation_jobs`. The backend updates `current_step`, `total_steps`, `current_section`, `progress_percent`, and status values while the synchronous generation endpoint runs. The frontend polls `/private-rfp/{rfp_id}/generation-progress` every five seconds only while the draft workspace is actively generating.

MCP generation now requires an explicit `confirm=true` parameter. Read-only tools do not require confirmation. MCP calls are audit logged with `source=mcp`.

## Ollama Local Model

Private chat uses Ollama through `http://localhost:11434`. The default model is `llama3.2:3b`, which is appropriate for a lightweight CPU-first MVP. Ollama is only called during chat, never during upload.

## Current Limitations

- No OCR for scanned PDFs.
- Vector search is local JSON storage and Python cosine similarity, not a production vector database.
- Draft generation is intentionally short and not a full proposal generator.
- DOCX formatting is basic.
- No authentication or user accounts.
- No PostgreSQL migration yet.
- No background processing pipeline.

## Future MCP Layer

A future phase may add an MCP layer for controlled local tool access and integrations. It is intentionally excluded from this MVP to keep the foundation small, auditable, and local-first.
