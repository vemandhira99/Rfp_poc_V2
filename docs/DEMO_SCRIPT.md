# Private RFP Tool Demo Script

1. Open the dashboard and point to the local-only banner and usage cards.
2. Open Settings and confirm private mode, Ollama health, and zero external AI calls.
3. Upload a tiny file and show it being classified as insufficient detail.
4. Upload the 25-page demo PDF and show the extracted text preview and metadata.
5. Show the guided workflow stepper and the primary next action.
6. Generate embeddings and point out that the app stays on this machine.
7. Open private chat and ask a simple RFP question.
8. Point out `provider`, `model_used`, source chunks, and `external_api_used=false`.
9. Open the draft workspace and start generation.
10. Show elapsed time, ETA, current section, and local CPU notice.
11. If generation is partial, explain that the valid sections were preserved and export is blocked until the draft is complete.
12. When complete, export DOCX.
13. Open the DOCX and point out that it contains generated content, not infrastructure errors.
14. Open Audit and export the activity trail.
15. Mention MCP confirmation for draft generation and the local-only security scan.

## Demo Talking Points

- The workflow is intentionally guided, not button-heavy.
- The app is local-first and does not call external AI providers.
- Failed generation never becomes a valid export.
- The audit trail and usage metrics are part of the proof story.

