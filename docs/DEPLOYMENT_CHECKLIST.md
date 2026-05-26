# Deployment Checklist

Use this checklist before pushing a release or triggering a Vercel deployment.

## Code And Build

- [ ] `frontend` builds successfully with `npm run build`
- [ ] `frontend` starts successfully with `npm run start`
- [ ] `backend` starts successfully with `start_backend.ps1` or Uvicorn
- [ ] No unexpected tracked files were produced by a local build
- [ ] `README.md` and docs still match the current architecture

## Local Runtime

- [ ] Ollama is running on the deployment machine if the backend is expected to use local AI
- [ ] `llama3.2:3b` is available in Ollama
- [ ] `nomic-embed-text` is available in Ollama
- [ ] `NEXT_PUBLIC_API_BASE_URL` points to the correct backend URL

## Data And Storage

- [ ] SQLite file path is correct for the backend environment
- [ ] Upload directory exists and is writable
- [ ] Export directory exists and is writable
- [ ] Any sample or scratch data is not accidentally included in the release scope

## Product Checks

- [ ] Upload flow works for PDF, DOCX, and TXT
- [ ] RFP detail pages load correctly
- [ ] Private chat returns grounded answers with source chunks
- [ ] Draft generation completes all 8 sections
- [ ] DOCX export succeeds on a completed draft
- [ ] Audit logs and usage summary load correctly

## Safety Checks

- [ ] No cloud AI provider paths were introduced
- [ ] Private mode remains the default runtime behavior
- [ ] MCP confirmation is still required for generation
- [ ] Failed or partial drafts do not export as valid DOCX

## Suggested Release Flow

1. Run the frontend build.
2. Verify backend health and Ollama status.
3. Open the main dashboard and confirm the upload, chat, and draft routes.
4. Generate a draft for one known-good RFP.
5. Export the DOCX and confirm the file opens.
6. Review audit logs for the main actions.
7. Push only after the checks pass.

