"use client";

import { useEffect, useMemo, useState } from "react";
import { ActionButton, ActionLink } from "@/components/ActionButton";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { ConfirmModal } from "@/components/ConfirmModal";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { PrivateChatPanel } from "@/components/PrivateChatPanel";
import { StatusBadge } from "@/components/StatusBadge";
import { AuditLogList } from "@/components/AuditLogList";
import { downloadDocx, embedRfp, exportDocx, generateShortDraft, getRfp, getRfpAuditLogs, refreshRfpMetadata, retrievalTest } from "@/lib/api";
import type { AuditLog, RetrievalTestResponse, RfpDocument } from "@/lib/types";
import { labelForRfpStatus } from "@/lib/ui-labels";

type StepState = "completed" | "current" | "pending" | "failed";

const STEP_DEFINITIONS = [
  { key: "uploaded", title: "Uploaded", description: "The file is in the workspace." },
  { key: "checked", title: "Checked", description: "We reviewed the text and readiness." },
  { key: "prepared", title: "Ready for Questions", description: "The document is ready for grounded answers." },
  { key: "questions", title: "Ask Questions", description: "Use the private assistant to explore the RFP." },
  { key: "draft", title: "Generate Draft", description: "Create a first draft for review." },
  { key: "export", title: "Export Word Document", description: "Create the Word file once the draft is valid." },
];

export default function RfpDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [rfpId, setRfpId] = useState<number | null>(null);
  const [rfp, setRfp] = useState<RfpDocument | null>(null);
  const [retrieval, setRetrieval] = useState<RetrievalTestResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirmDraft, setConfirmDraft] = useState(false);

  useEffect(() => {
    params.then((value) => setRfpId(Number(value.id)));
  }, [params]);

  useEffect(() => {
    if (rfpId) refresh(rfpId);
  }, [rfpId]);

  async function refresh(id = rfpId) {
    if (!id) return;
    setLoading("loading");
    try {
      const [rfpData, logs] = await Promise.all([getRfp(id), getRfpAuditLogs(id, 8)]);
      setRfp(rfpData);
      setAuditLogs(logs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the RFP workspace.");
    } finally {
      setLoading("");
    }
  }

  async function onRefreshDetails() {
    if (!rfpId) return;
    setLoading("refresh-details");
    try {
      await refreshRfpMetadata(rfpId);
      await refresh(rfpId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not refresh metadata details.");
    } finally {
      setLoading("");
    }
  }

  async function onPrepare() {
    if (!rfpId) return;
    setLoading("preparing");
    try {
      await embedRfp(rfpId);
      await refresh(rfpId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preparing for chat failed.");
    } finally {
      setLoading("");
    }
  }

  async function onRetrievalTest() {
    if (!rfpId) return;
    setLoading("retrieval");
    try {
      setRetrieval(await retrievalTest(rfpId, "scope requirements deadline"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search test failed.");
    } finally {
      setLoading("");
    }
  }

  async function startDraft() {
    if (!rfpId) return;
    setConfirmDraft(false);
    setLoading("draft");
    try {
      await generateShortDraft(rfpId, true);
      window.location.href = `/rfps/${rfpId}/draft`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft generation failed.");
      setLoading("");
    }
  }

  async function onExport() {
    if (!rfpId) return;
    setLoading("export");
    try {
      await exportDocx(rfpId);
      window.location.href = downloadDocx(rfpId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed. Generate a valid draft first.");
    } finally {
      setLoading("");
    }
  }

  const primaryAction = useMemo(() => {
    if (!rfp) return null;
    if (isGenerationRunning(rfp)) {
      return { kind: "button" as const, label: "Draft Running", onClick: () => undefined };
    }
    const draftReady = rfp.status === "draft_generated" || rfp.generation_status === "completed";
    const hasEmbeddings =
      (rfp.embedded_chunk_count ?? 0) > 0 ||
      rfp.embedding_status === "completed" ||
      rfp.embedding_status === "partial";
    if (draftReady) {
      return { kind: "link" as const, label: "Open Draft Workspace", href: `/rfps/${rfp.id}/draft` };
    }
    if (rfp.document_quality === "needs_more_detail" || rfp.document_quality === "insufficient_rfp_detail") {
      return { kind: "link" as const, label: "Upload Better File", href: "/upload" };
    }
    if (rfp.document_quality === "extraction_needs_review") {
      return { kind: "link" as const, label: "Review Document", href: "/upload" };
    }
    if (!hasEmbeddings) {
      return { kind: "button" as const, label: "Prepare for Chat", onClick: onPrepare };
    }
    if (rfp.status === "ready_for_private_chat" || hasEmbeddings) {
      return { kind: "button" as const, label: "Ask Questions", onClick: focusChat };
    }
    return { kind: "button" as const, label: "Generate Draft", onClick: () => setConfirmDraft(true) };
  }, [rfp]);

  const stepState = useMemo(() => {
    const interrupted = Boolean(rfp && rfp.status === "failed_stale");
    const checked = Boolean(rfp && rfp.document_quality !== "needs_more_detail" && rfp.document_quality !== "insufficient_rfp_detail");
    const prepared = Boolean(rfp && ((rfp.embedded_chunk_count ?? 0) > 0 || rfp.embedding_status === "completed" || rfp.embedding_status === "partial"));
    const canAsk = Boolean(rfp && prepared && rfp.status !== "needs_more_detail");
    const draftReady = Boolean(rfp && (rfp.status === "draft_generated" || rfp.generation_status === "completed"));
    const exported = auditLogs.some((log) => log.action === "docx_exported");

    return new Map<string, StepState>([
      ["uploaded", "completed"],
      ["checked", interrupted ? "failed" : checked ? "completed" : "current"],
      ["prepared", prepared ? "completed" : checked ? "current" : "pending"],
      ["questions", canAsk || draftReady ? "completed" : prepared ? "current" : "pending"],
      ["draft", draftReady ? "completed" : canAsk ? "current" : "pending"],
      ["export", exported ? "completed" : draftReady ? "current" : "pending"],
    ]);
  }, [rfp, auditLogs]);

  const workspaceSummary = useMemo(
    () => ({
      client: rfp?.probable_client || "Not found",
      deadline: rfp?.probable_deadline || "Not found",
      size: rfp ? `${rfp.word_count.toLocaleString()} words` : "0 words",
      readiness:
        !rfp || rfp.document_quality === "needs_more_detail" || rfp.document_quality === "insufficient_rfp_detail"
          ? "Needs Attention"
          : rfp.document_quality === "extraction_needs_review"
            ? "Text Extraction Issue"
            : "Ready",
      draft: isGenerationRunning(rfp)
        ? "Draft Running"
        : rfp?.status === "draft_generated" || rfp?.generation_status === "completed"
          ? "Draft Ready"
          : rfp?.status === "failed_stale"
            ? "Interrupted"
            : labelForRfpStatus(rfp?.status ?? "not_started"),
    }),
    [rfp],
  );

  return (
    <>
      <PageHeader
        title={rfp?.probable_title || rfp?.title || "RFP Detail"}
        description="Review the document, ask questions, and move toward a draft."
        action={
          <div className="flex flex-wrap gap-2">
            <StatusBadge value={rfp?.document_quality || "not_started"} />
            <StatusBadge value={isGenerationRunning(rfp) ? "running" : rfp?.status || "not_started"} />
          </div>
        }
      />

      {error ? <div className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}

      {rfp ? (
        <div className="space-y-6">
      <Card>
            <CardBody className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <SummaryCard label="Client" value={workspaceSummary.client} />
              <SummaryCard label="Deadline" value={workspaceSummary.deadline} />
              <SummaryCard label="Document Size" value={workspaceSummary.size} />
              <SummaryCard label="Readiness" value={workspaceSummary.readiness} />
              <SummaryCard label="Draft Status" value={workspaceSummary.draft} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Guided Workflow" subtitle="One clear path from upload to export." />
            <CardBody>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {STEP_DEFINITIONS.map((step) => (
                  <WorkflowStep
                    key={step.key}
                    title={step.title}
                    description={step.description}
                    state={stepState.get(step.key) ?? "pending"}
                  />
                ))}
              </div>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                {primaryAction?.kind === "link" ? (
                  <ActionLink href={primaryAction.href} variant="primary">
                    {primaryAction.label}
                  </ActionLink>
                ) : primaryAction?.kind === "button" ? (
                  <ActionButton variant="primary" onClick={primaryAction.onClick} disabled={Boolean(loading) || isGenerationRunning(rfp)}>
                    {loading === "preparing" ? "Preparing..." : isGenerationRunning(rfp) ? "Draft Running" : primaryAction.label}
                  </ActionButton>
                ) : (
                  <ActionButton variant="primary" onClick={() => setConfirmDraft(true)} disabled={Boolean(loading)}>
                    Generate Draft
                  </ActionButton>
                )}
                {rfp.embedding_status === "completed" ? (
                  <ActionButton onClick={focusChat}>Open Chat</ActionButton>
                ) : null}
                <details className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm">
                  <summary className="cursor-pointer font-semibold text-slate-700">View details</summary>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <StatusBadge value={rfp.document_quality} />
                    <StatusBadge value={rfp.embedding_status ?? "not_started"} />
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-600">
                      {rfp.chunk_count} sections
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-600">
                      {rfp.embedded_chunk_count ?? 0} ready for questions
                    </span>
                  </div>
                </details>
              </div>
            </CardBody>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
            <aside className="space-y-6">
              <Card>
                <CardHeader
                  title="Business Metadata"
                  subtitle="Simple extracted details."
                  action={<ActionButton onClick={onRefreshDetails} disabled={loading === "refresh-details"}>{loading === "refresh-details" ? "Refreshing..." : "Refresh Details"}</ActionButton>}
                />
                <CardBody className="grid gap-3">
                  <MetaCard label="Client" value={rfp.probable_client || "Not found"} />
                  <MetaCard label="Deadline" value={rfp.probable_deadline || "Not found"} />
                  <MetaCard label="Submission Date" value={rfp.probable_submission_date || "Not found"} />
                  <MetaCard label="Title" value={rfp.probable_title || rfp.title || "Not found"} />
                  {rfp.metadata_confidence != null ? <MetaCard label="Extraction Confidence" value={`${Math.round(rfp.metadata_confidence * 100)}%`} /> : null}
                </CardBody>
                {rfp.metadata_reason ? <div className="border-t border-slate-200 px-6 py-4 text-sm text-slate-600">Why this was chosen: {rfp.metadata_reason}</div> : null}
                {rfp.metadata_source_snippet ? <div className="border-t border-slate-200 px-6 py-4 text-sm text-slate-600">Source snippet: {rfp.metadata_source_snippet}</div> : null}
              </Card>

              {retrieval ? (
                <Card>
                  <CardHeader title="Section Preview" subtitle="A quick view of the matching sections." />
                  <CardBody className="space-y-3">
                    {retrieval.results.map((chunk) => (
                      <div key={chunk.chunk_id} className="rounded-2xl bg-slate-50 p-4 text-sm">
                        <div className="font-semibold text-slate-950">
                          Section {chunk.chunk_id} · {chunk.score.toFixed(3)}
                        </div>
                        <p className="mt-2 line-clamp-4 text-slate-600">{chunk.preview}</p>
                      </div>
                    ))}
                  </CardBody>
                </Card>
              ) : null}

              <Card>
                  <CardHeader title="Activity Log" subtitle="Latest actions for this RFP." />
                <CardBody>
                  <AuditLogList logs={auditLogs} />
                </CardBody>
              </Card>
            </aside>

            {rfpId ? <div id="private-chat-panel"><PrivateChatPanel rfpId={rfpId} inputId={`private-chat-input-${rfpId}`} /></div> : null}
          </div>
        </div>
      ) : (
        <Card>
          <CardBody>{loading ? <EmptyState title="Loading RFP" detail="Please wait while the workspace loads." /> : <EmptyState title="RFP not found" detail="Check the link and try again." />}</CardBody>
        </Card>
      )}

      <ConfirmModal
        open={confirmDraft}
        title="Start Local Draft Generation?"
        text="This runs on your laptop and may take 15-30 minutes for larger RFPs. Your document stays local."
        confirmLabel="Start Generation"
        onCancel={() => setConfirmDraft(false)}
        onConfirm={startDraft}
      />
    </>
  );
}

function focusChat() {
  document.getElementById("private-chat-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  const input = document.querySelector<HTMLInputElement | HTMLTextAreaElement>("[id^='private-chat-input-']");
  input?.focus();
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function MetaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function WorkflowStep({
  title,
  description,
  state,
}: {
  title: string;
  description: string;
  state: StepState;
}) {
  const styles: Record<StepState, string> = {
    completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
    current: "border-slate-300 bg-slate-950 text-white",
    pending: "border-slate-200 bg-white text-slate-500",
    failed: "border-rose-200 bg-rose-50 text-rose-700",
  };
  const stateLabel: Record<StepState, string> = {
    completed: "Completed",
    current: "Current",
    pending: "Pending",
    failed: "Failed",
  };

  return (
    <div className={`rounded-[20px] border p-4 ${styles[state]}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-semibold">{title}</div>
        <span className="text-xs font-semibold uppercase tracking-wide opacity-80">{stateLabel[state]}</span>
      </div>
      <p className="mt-2 text-sm leading-6 opacity-90">{description}</p>
    </div>
  );
}

function isGenerationRunning(rfp: RfpDocument | null) {
  return rfp?.generation_status === "queued" || rfp?.generation_status === "running";
}
