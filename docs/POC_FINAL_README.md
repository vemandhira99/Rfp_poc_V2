# Private RFP Tool Final POC README

Private RFP Tool is a local-first enterprise POC for private RFP analysis. It lets a team upload RFPs, validate extracted text, create local embeddings, ask grounded questions, generate a short draft, export DOCX, and review an audit trail. Everything stays on the Windows laptop.

## Final Workflow

1. Upload RFP
2. Validate document quality
3. Generate embeddings
4. Ask private chat questions
5. Generate a short draft
6. Export DOCX
7. Review audit proof

## Local Privacy Model

- Ollama runs locally at `http://localhost:11434`.
- Chat model: `llama3.2:3b`
- Embedding model: `nomic-embed-text`
- No Gemini, Azure, OpenAI, Claude, LangChain, or LangGraph runtime is used in private mode.
- Uploads, chunks, embeddings, drafts, exports, and audit logs stay local.

## What Happens If Ollama Is Offline

- The shared Ollama health check marks the runtime unavailable.
- Chat returns a friendly local error instead of calling a model.
- Embedding generation stops before work starts.
- Draft generation does not start.
- DOCX export refuses to save a completed draft if the draft is invalid or incomplete.

## Why Failed Drafts Are Blocked

- Generation checks Ollama health before starting.
- Any infrastructure error such as Ollama offline, model missing, connection refused, timeout, or traceback text marks the job failed or failed_partial.
- Invalid section text is rejected before save.
- DOCX export validates that all 8 sections exist, the job completed, and no infrastructure error text is present.

## Progress And ETA

The draft workspace shows:

- current section
- current step
- elapsed time
- estimated remaining time
- estimated total time
- progress percent
- model used
- `external_api_used=false`

The estimate improves after the first completed section.

## Usage Metrics

Local usage tracking records:

- prompt words
- response words
- estimated tokens
- elapsed seconds
- retrieval chunks used
- model used
- `external_api_used=false`

These values are for observability only. No paid API tokens are consumed.

## Known Limitations

- OCR is not implemented yet.
- Draft generation is intentionally short and needs human review.
- ETA values are approximate on CPU.
- Metadata extraction is heuristic and may miss some documents.

## Demo Notes

- Keep Ollama running before the demo.
- Confirm both local models are present.
- Use the guided workflow rather than the advanced routes.
- Use the audit trail to prove local-only behavior.

