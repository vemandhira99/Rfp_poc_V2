export function humanize(value: string) {
  return value.replaceAll("_", " ");
}

export function labelForDocumentQuality(value: string) {
  const labels: Record<string, string> = {
    valid_rfp: "Ready",
    limited_but_valid: "Ready",
    insufficient_rfp_detail: "Needs Better Document",
    extraction_needs_review: "Text Extraction Issue",
    needs_more_detail: "Needs Better Document",
    not_applicable: "N/A",
  };

  return labels[value] ?? humanize(value);
}

export function labelForRfpStatus(value: string) {
  const labels: Record<string, string> = {
    uploaded: "Uploaded",
    needs_more_detail: "Needs Better Document",
    extraction_needs_review: "Text Extraction Issue",
    ready_for_private_chat: "Ready for Chat",
    draft_generated: "Draft Ready",
    generation_failed: "Draft Failed",
    failed_partial: "Partial Draft",
    failed_stale: "Interrupted",
    not_started: "Not Started",
    completed: "Complete",
    partial: "Partial",
    not_applicable: "N/A",
    needs_human_review: "Needs Human Review",
  };

  return labels[value] ?? humanize(value);
}

export function labelForEmbeddingStatus(value: string) {
  const labels: Record<string, string> = {
    completed: "Ready for Chat",
    running: "Preparing",
    failed: "Issue",
    not_started: "Not Started",
    queued: "Queued",
  };

  return labels[value] ?? humanize(value);
}

export function labelForDraftState(value: string) {
  const labels: Record<string, string> = {
    not_started: "Not Started",
    queued: "Queued",
    running: "Running",
    completed: "Draft Ready",
    failed: "Draft Failed",
    failed_partial: "Partial Draft",
    failed_stale: "Interrupted",
  };

  return labels[value] ?? humanize(value);
}

export function labelForGenerationStep(value?: string | null) {
  if (!value) return "Waiting";
  const labels: Record<string, string> = {
    starting: "Starting",
    embedding: "Preparing for Chat",
    drafting: "Generating Draft",
    exporting: "Exporting",
    validation: "Checking Draft",
  };
  return labels[value] ?? humanize(value);
}

export function friendlyStatusLabel(value: string) {
  const labels: Record<string, string> = {
    valid_rfp: "Ready",
    limited_but_valid: "Ready",
    insufficient_rfp_detail: "Needs Better Document",
    extraction_needs_review: "Text Extraction Issue",
    needs_more_detail: "Needs Better Document",
    ready_for_private_chat: "Ready for Chat",
    draft_generated: "Draft Ready",
    generation_failed: "Draft Failed",
    failed_partial: "Partial Draft",
    failed_stale: "Interrupted",
    uploaded: "Uploaded",
    not_started: "Not Started",
    running: "Running",
    queued: "Queued",
    completed: "Complete",
    partial: "Partial",
    not_applicable: "N/A",
    needs_human_review: "Needs Human Review",
  };

  return labels[value] ?? humanize(value);
}

export function labelForAuditAction(action: string) {
  const labels: Record<string, string> = {
    upload: "Upload",
    classification: "Document Check",
    embeddings_generated: "Prepared for Chat",
    chat_question: "Chat Question",
    generation_started: "Draft Generation Started",
    generation_completed: "Draft Generation Completed",
    generation_failed: "Draft Generation Failed",
    docx_exported: "Word Exported",
    invalid_demo_draft_repaired: "Demo Draft Repaired",
    private_chat: "Private Chat",
  };

  return labels[action] ?? humanize(action);
}
