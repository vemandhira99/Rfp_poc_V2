import type {
  ChatResponse,
  ChatHistoryItem,
  DraftGenerationResponse,
  DraftSection,
  EmbedResponse,
  ExportDocxResponse,
  AuditLog,
  GenerationProgress,
  HealthResponse,
  OllamaStatus,
  QualityReport,
  RetrievalTestResponse,
  RfpDocument,
  SourceChunk,
  UploadResult,
  RfpUsage,
  UsageSummary,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    let message = detail || `Request failed with ${response.status}`;
    try {
      const parsed = JSON.parse(detail);
      message = parsed.message || parsed.detail || parsed.error || message;
    } catch {
      // Fall back to the raw text body.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getRfps(): Promise<RfpDocument[]> {
  return request<RfpDocument[]>("/rfps");
}

export const listRfps = getRfps;

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getRfp(id: number): Promise<RfpDocument> {
  return request<RfpDocument>(`/rfps/${id}`);
}

export function refreshRfpMetadata(id: number): Promise<RfpDocument> {
  return request<RfpDocument>(`/rfps/${id}/refresh-metadata`, { method: "POST" });
}

export function getOllamaStatus(): Promise<OllamaStatus> {
  return request<OllamaStatus>("/private-rfp/ollama/status");
}

export function getChunks(id: number): Promise<SourceChunk[]> {
  return request<SourceChunk[]>(`/rfps/${id}/chunks`);
}

export function embedRfp(id: number): Promise<EmbedResponse> {
  return request<EmbedResponse>(`/rfps/${id}/embed`, { method: "POST" });
}

export function retrievalTest(id: number, query: string, mode = "hybrid"): Promise<RetrievalTestResponse> {
  const params = new URLSearchParams({ q: query, mode });
  return request<RetrievalTestResponse>(`/rfps/${id}/retrieval-test?${params.toString()}`);
}

export async function uploadRfp(file: File): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadResult>("/uploads/rfp", {
    method: "POST",
    body: formData,
  });
}

export function askRfpQuestion(rfpId: number, question: string): Promise<ChatResponse> {
  return request<ChatResponse>(`/private-rfp/${rfpId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export const chatWithRfp = askRfpQuestion;

export function getChatHistory(rfpId: number, limit = 20): Promise<ChatHistoryItem[]> {
  return request<ChatHistoryItem[]>(`/private-rfp/${rfpId}/chat-history?limit=${limit}`);
}

export function generateShortDraft(rfpId: number, confirmRegenerate = false): Promise<DraftGenerationResponse> {
  const params = new URLSearchParams();
  if (confirmRegenerate) params.set("confirm_regenerate", "true");
  const suffix = params.toString();
  return request<DraftGenerationResponse>(`/private-rfp/${rfpId}/generate-short-draft${suffix ? `?${suffix}` : ""}`, { method: "POST" });
}

export function getDraft(rfpId: number): Promise<DraftSection[]> {
  return request<DraftSection[]>(`/private-rfp/${rfpId}/draft`);
}

export function getQuality(rfpId: number): Promise<QualityReport> {
  return request<QualityReport>(`/private-rfp/${rfpId}/quality`);
}

export function exportDocx(rfpId: number): Promise<ExportDocxResponse> {
  return request<ExportDocxResponse>(`/private-rfp/${rfpId}/export-docx`, { method: "POST" });
}

export function downloadDocx(rfpId: number): string {
  return `${API_BASE_URL}/private-rfp/${rfpId}/download`;
}

export function getGenerationProgress(rfpId: number): Promise<GenerationProgress> {
  return request<GenerationProgress>(`/private-rfp/${rfpId}/generation-progress`);
}

export function getUsageSummary(): Promise<UsageSummary> {
  return request<UsageSummary>("/usage/summary");
}

export function getRfpUsage(rfpId: number): Promise<RfpUsage> {
  return request<RfpUsage>(`/rfps/${rfpId}/usage`);
}

export function getAuditLogs(limit = 100): Promise<AuditLog[]> {
  return request<AuditLog[]>(`/audit/logs?limit=${limit}`);
}

export function auditExportUrl(params?: { rfpId?: string; limit?: number }): string {
  const search = new URLSearchParams();
  if (params?.rfpId) search.set("rfp_id", params.rfpId);
  if (params?.limit) search.set("limit", String(params.limit));
  const suffix = search.toString();
  return `${API_BASE_URL}/audit/export${suffix ? `?${suffix}` : ""}`;
}

export function getRfpAuditLogs(rfpId: number, limit = 50): Promise<AuditLog[]> {
  return request<AuditLog[]>(`/rfps/${rfpId}/audit?limit=${limit}`);
}
