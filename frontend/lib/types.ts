export type RfpDocument = {
  id: number;
  title: string | null;
  original_filename: string;
  file_type: string;
  file_size: number;
  page_count: number;
  word_count: number;
  character_count: number;
  line_count: number;
  probable_title?: string | null;
  probable_client?: string | null;
  probable_deadline?: string | null;
  probable_submission_date?: string | null;
  metadata_confidence?: number | null;
  metadata_reason?: string | null;
  generation_job_id?: number | null;
  generation_status?: string | null;
  generation_current_section?: string | null;
  generation_progress_percent?: number | null;
  generation_updated_at?: string | null;
  generation_started_at?: string | null;
  metadata_source_snippet?: string | null;
  document_quality: string;
  classification_reason: string | null;
  status: string;
  chunk_count: number;
  embedded_chunk_count: number;
  embedding_status: string;
  created_at: string;
  updated_at: string;
  extracted_text?: string | null;
};

export type UploadResult = {
  rfp_id: number;
  original_filename: string;
  stored_filename: string;
  file_type: string;
  file_size: number;
  page_count: number;
  word_count: number;
  character_count: number;
  line_count: number;
  extracted_text_preview: string | null;
  probable_title: string | null;
  probable_client: string | null;
  probable_deadline: string | null;
  probable_submission_date: string | null;
  metadata_confidence?: number | null;
  metadata_reason?: string | null;
  document_quality: string;
  status: string;
  reason: string;
  chunk_count: number;
  external_api_used: boolean;
};

export type SourceChunk = {
  chunk_id: number;
  chunk_order: number;
  section_title: string | null;
  page_number: number | null;
  score: number;
  retrieval_type: string | null;
  chunk_text: string;
  preview: string;
};

export type ChatResponse = {
  rfp_id: number;
  answer: string;
  provider: string;
  model_used: string | null;
  intent?: string | null;
  retrieval_mode: string;
  external_api_used: boolean;
  source_chunks: SourceChunk[];
  code?: string | null;
};

export type ChatHistoryItem = {
  role: "user" | "assistant";
  message: string;
  provider: string | null;
  model_used: string | null;
  intent?: string | null;
  source_chunks_json?: string | null;
  created_at: string;
};

export type OllamaStatus = {
  available: boolean;
  chat_model_available: boolean;
  embedding_model_available: boolean;
  chat_model: string;
  embedding_model: string;
  models: string[];
  ollama_base_url: string;
  message: string | null;
  checked_at: string;
};

export type HealthResponse = {
  status: string;
  service: string;
  mode: string;
};

export type EmbedResponse = {
  rfp_id: number;
  embedding_status: string;
  embedded_chunks: number;
  failed_chunks: number;
  external_api_used: boolean;
  already_prepared?: boolean;
};

export type RetrievalTestResponse = {
  query: string;
  mode: string;
  results: SourceChunk[];
};

export type DraftSection = {
  id: number;
  rfp_id: number;
  section_order: number;
  section_title: string;
  section_content: string;
  model_used: string | null;
  provider: string;
  retrieval_summary_json: string | null;
  word_count: number;
  quality_status: string;
  validation_status?: string;
  validation_issues?: string[];
  has_infrastructure_error?: boolean;
  created_at: string;
  updated_at: string;
};

export type DraftGenerationResponse = {
  rfp_id: number;
  status: string;
  sections_generated: number;
  provider: string;
  external_api_used: boolean;
  job_id: number;
  error?: string;
};

export type QualityCheck = {
  name: string;
  status: string;
  message: string;
};

export type QualityReport = {
  overall_status: string;
  checks: QualityCheck[];
  external_api_used?: boolean;
};

export type ExportDocxResponse = {
  rfp_id: number;
  export_id: number;
  file_path: string;
  file_name: string;
  page_estimate: number | null;
  word_count: number;
  quality_report: QualityReport;
  external_api_used: boolean;
};

export type AuditLog = {
  id: number;
  event_type: string;
  entity_type: string | null;
  entity_id: number | null;
  rfp_id: number | null;
  action: string;
  actor: string;
  source: string | null;
  details_json: string | null;
  external_api_used: boolean;
  created_at: string;
};

export type GenerationProgress = {
  rfp_id: number;
  job_id: number | null;
  status: "not_started" | "queued" | "running" | "completed" | "failed" | "failed_partial" | "failed_stale";
  current_step: number;
  total_steps: number;
  current_section: string | null;
  progress_percent: number;
  error_message?: string | null;
  external_api_used: boolean;
  started_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
  elapsed_seconds?: number | null;
  estimated_total_seconds?: number | null;
  estimated_remaining_seconds?: number | null;
  average_seconds_per_section?: number | null;
  model_used?: string | null;
};

export type UsageSummary = {
  total_calls: number;
  estimated_total_tokens: number;
  total_elapsed_seconds: number;
  external_ai_calls: number;
  local_ai_calls: number;
  local_only: boolean;
  checked_at: string;
};

export type UsageEntry = {
  id: number;
  operation_type: string;
  model_used: string | null;
  prompt_word_count: number;
  response_word_count: number;
  estimated_prompt_tokens: number;
  estimated_response_tokens: number;
  estimated_total_tokens: number;
  elapsed_seconds: number | null;
  retrieval_chunks_used: number;
  external_api_used: boolean;
  created_at: string;
};

export type RfpUsage = {
  rfp_id: number;
  total_calls: number;
  estimated_total_tokens: number;
  total_elapsed_seconds: number;
  external_ai_calls: number;
  entries: UsageEntry[];
};
