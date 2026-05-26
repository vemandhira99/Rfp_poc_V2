# API Contract

Base URL: `http://localhost:8000`

## GET /health

Response:

```json
{
  "status": "ok",
  "service": "Private RFP Tool",
  "mode": "private"
}
```

## POST /uploads/rfp

Multipart form field: `file`

Supported file types: PDF, DOCX, TXT

Response:

```json
{
  "rfp_id": 1,
  "original_filename": "sample.txt",
  "stored_filename": "uuid.txt",
  "file_type": "txt",
  "file_size": 2048,
  "page_count": 1,
  "word_count": 650,
  "character_count": 4200,
  "line_count": 40,
  "document_quality": "valid_rfp",
  "status": "ready_for_private_chat",
  "reason": "Document contains enough text for private local analysis.",
  "chunk_count": 1,
  "external_api_used": false
}
```

## GET /rfps

Returns uploaded RFP summaries.

## GET /rfps/{rfp_id}

Returns one uploaded RFP, including extracted text, `chunk_count`, `embedded_chunk_count`, and `embedding_status`.

## GET /rfps/{rfp_id}/chunks

Returns local chunks for the selected RFP.

## POST /rfps/{rfp_id}/embed

Generates local Ollama embeddings for every chunk that does not already have one.

Response:

```json
{
  "rfp_id": 1,
  "embedding_status": "completed",
  "embedded_chunks": 12,
  "failed_chunks": 0,
  "external_api_used": false
}
```

## GET /rfps/{rfp_id}/retrieval-test?q=deadline%20requirements%20scope

Tests retrieval using `mode=hybrid` by default. Supported modes are `lexical`, `vector`, and `hybrid`.

Response:

```json
{
  "query": "deadline requirements scope",
  "mode": "hybrid",
  "results": [
    {
      "chunk_id": 1,
      "chunk_order": 1,
      "section_title": null,
      "page_number": null,
      "score": 0.82,
      "retrieval_type": "hybrid",
      "chunk_text": "Full chunk text...",
      "preview": "Short chunk preview..."
    }
  ]
}
```

## POST /private-rfp/{rfp_id}/chat

Request:

```json
{
  "question": "What is this RFP about?"
}
```

## POST /private-rfp/{rfp_id}/generate-short-draft

Generates a controlled private short response draft using local Ollama chat and retrieved RFP excerpts. Generation is sequential, one section at a time.

Response:

```json
{
  "rfp_id": 1,
  "status": "completed",
  "sections_generated": 8,
  "provider": "local_ollama",
  "external_api_used": false
}
```

## GET /private-rfp/{rfp_id}/draft

Returns draft sections ordered by `section_order`.

## GET /private-rfp/{rfp_id}/quality

Returns deterministic draft quality checks.

Response:

```json
{
  "overall_status": "needs_human_review",
  "checks": [
    {
      "name": "human_review_required",
      "status": "required",
      "message": "Human proposal team review is required before use."
    }
  ]
}
```

## POST /private-rfp/{rfp_id}/export-docx

Exports the latest private short draft to DOCX under `storage/exports`.

Response:

```json
{
  "rfp_id": 1,
  "export_id": 1,
  "file_path": "storage/exports/rfp_1_private_short_draft.docx",
  "file_name": "rfp_1_private_short_draft.docx",
  "page_estimate": 8,
  "word_count": 2800,
  "quality_report": {
    "overall_status": "needs_human_review",
    "checks": []
  },
  "external_api_used": false
}
```

## GET /private-rfp/{rfp_id}/download

Downloads the latest generated DOCX export.

## GET /private-rfp/{rfp_id}/generation-progress

Returns the latest local draft generation job state.

```json
{
  "rfp_id": 1,
  "job_id": 1,
  "status": "running",
  "current_step": 3,
  "total_steps": 8,
  "current_section": "Proposed Solution Approach",
  "progress_percent": 37,
  "external_api_used": false
}
```

## GET /audit/logs

Returns latest audit logs, newest first.

## GET /rfps/{rfp_id}/audit

Returns latest audit logs for one RFP, newest first.

Response:

```json
{
  "rfp_id": 1,
  "answer": "The uploaded RFP describes...",
  "provider": "local_ollama",
  "model_used": "llama3.2:3b",
  "retrieval_mode": "hybrid",
  "external_api_used": false,
  "source_chunks": [
    {
      "chunk_id": 1,
      "chunk_order": 1,
      "section_title": null,
      "page_number": null,
      "score": 3.0,
      "chunk_text": "Full chunk text...",
      "preview": "Short chunk preview..."
    }
  ]
}
```
