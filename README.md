# Private RFP Tool

Private RFP Tool is a local-first workspace for reviewing RFPs, searching them with grounded retrieval, chatting privately against uploaded content, generating short draft responses, and exporting results for review.

This build is designed to keep data on the local machine. The backend uses SQLite and local storage, and the AI runtime is expected to be Ollama running on the same machine.

## What This Build Does

The current application supports the full private RFP workflow:

1. Upload PDF, DOCX, or TXT files.
2. Extract text and metadata from the source document.
3. Classify the document and assess quality.
4. Split the content into chunks for retrieval.
5. Generate local embeddings with Ollama when available.
6. Ask grounded questions in private chat with source references.
7. Generate an eight-section short draft locally.
8. Export the draft to DOCX.
9. Track audit logs and local usage metrics.

## Architecture

```text
Browser
  -> Next.js frontend
  -> FastAPI backend
  -> SQLite database
  -> local file storage
  -> Ollama for chat and embeddings

MCP client
  -> local MCP server
  -> existing backend services
  -> SQLite / local storage / Ollama
```

### Frontend

- Framework: Next.js 16 with the App Router
- Language: TypeScript
- Styling: Tailwind CSS
- UI role: dashboard, upload flow, chat, draft review, audit view, usage view, and settings

Frontend routes in this build:

- `/` dashboard
- `/upload` upload and document review
- `/dashboard` workspace overview
- `/audit` audit logs
- `/chat` private chat workspace
- `/drafts` draft overview
- `/settings` local runtime and privacy status
- `/rfps/[id]` RFP detail and chat
- `/rfps/[id]/draft` generated draft review

The frontend talks to the backend through `NEXT_PUBLIC_API_BASE_URL`, which defaults to `http://127.0.0.1:8001`.

### Backend

- Framework: FastAPI
- Database layer: SQLAlchemy
- Database: SQLite for the MVP
- File handling: local upload storage under `backend/storage`
- AI runtime: Ollama
- Local automation: MCP server wrapping the existing backend services

The backend exposes routes for:

- health and Ollama status
- uploads and parsing
- RFP listing and document metadata
- chunk retrieval and retrieval tests
- private chat
- short draft generation
- DOCX export and download
- audit logs
- usage summary

## Core Services

The backend is organized around a small set of focused services:

- Upload and parsing service
- Deterministic classification service
- Metadata extraction service
- Chunking and embedding service
- Hybrid retrieval service
- Private chat service
- Private draft generation service
- DOCX export service
- Audit service
- Usage service
- Shared Ollama health service

## Data Flow

### 1. Upload

The user uploads a PDF, DOCX, or TXT file. The backend stores the original file locally and creates an RFP record in SQLite.

### 2. Parse and Classify

Text is extracted, metadata is inferred, and document quality is scored. The app uses those signals to decide whether the file is ready for chat, needs review, or needs a better source document.

### 3. Chunk and Embed

The document is split into source chunks. If Ollama embeddings are available, the chunks are embedded locally and stored in the database.

### 4. Retrieve and Chat

Private chat uses hybrid retrieval:

- semantic retrieval when embeddings exist
- lexical fallback when embeddings are missing or unavailable
- source chunks are returned with answers for reviewability

### 5. Draft Generation

The short draft is generated section by section. The generation flow is intentionally controlled:

- it checks Ollama health first
- it runs locally only
- it tracks progress, ETA, and elapsed time
- it refuses to export unless all expected sections exist

### 6. Export

Once a full draft is ready, the backend can export the content to DOCX for review and sharing.

## Local AI Runtime

This build expects Ollama to be available locally.

Default models in the backend config:

- Chat model: `llama3.2:3b`
- Embedding model: `nomic-embed-text`

Default Ollama base URL:

- `http://localhost:11434`

If Ollama is unavailable, the shared health check reports it and the UI reflects that state. Chat, embeddings, and draft generation all rely on the same health signal.

## Security and Privacy Model

The app is intentionally private-first:

- no cloud AI providers are used in the MVP path
- uploaded content stays local
- audit logs are kept for important actions
- generation requires a healthy local runtime
- MCP generation requires confirmation
- failed generation outputs are not treated as valid draft content

## Repository Layout

```text
backend/
  app/              FastAPI application, services, models, schemas
  mcp_server/       Local MCP wrapper around backend services
  storage/          Uploaded files, exports, and local artifacts
  start_backend.ps1 Backend startup script for Windows
frontend/
  app/              Next.js routes and pages
  components/       Reusable UI components
  lib/              API client and shared frontend types
docs/               Architecture notes, demo script, readiness docs, API contract
scratch/            Demo data, diagnostics, and exploratory scripts
```

## Prerequisites

- Node.js 20+ recommended
- Python 3.12+
- Ollama running locally
- Ollama models pulled locally

Recommended Ollama setup:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## Backend Setup

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
.\start_backend.ps1
```

The backend listens on:

- `http://127.0.0.1:8001`

## Frontend Setup

From the `frontend` directory:

```powershell
npm install
npm run dev
```

The frontend listens on:

- `http://localhost:3000`

If the backend is running on a different host or port, update `frontend/.env` or set:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8001"
```

## Production Build

Frontend build:

```powershell
cd frontend
npm run build
```

Frontend production start:

```powershell
npm run start
```

The backend can be run with Uvicorn directly if you prefer:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload --reload-dir app
```

## Deployment Notes

- The frontend is Vercel-friendly.
- The backend is expected to run separately because it depends on local storage, SQLite, and Ollama.
- Keep `NEXT_PUBLIC_API_BASE_URL` pointed at the backend instance you want the UI to talk to.
- Make sure the Ollama host and models are available on the machine running the backend.

## Troubleshooting

- If the UI shows Ollama offline, verify that `ollama serve` is running and the models are installed.
- If uploads fail, check that the backend process can write to `backend/storage/uploads`.
- If build or runtime state looks stale, remove the local `.next` folder and rebuild the frontend.
- If draft export fails, confirm that all eight draft sections were generated successfully.

## Related Docs

- [Architecture notes](docs/ARCHITECTURE_FINAL.md)
- [Final POC README](docs/POC_FINAL_README.md)
- [API contract](docs/api_contract.md)
- [Demo script](docs/DEMO_SCRIPT.md)

