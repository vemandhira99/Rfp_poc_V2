"use client";

import { useEffect, useMemo, useState } from "react";
import { ActionButton } from "@/components/ActionButton";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { ConfirmModal } from "@/components/ConfirmModal";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { downloadDocx, exportDocx, generateShortDraft, getDraft, getGenerationProgress, getQuality, getRfp } from "@/lib/api";
import type { DraftSection, ExportDocxResponse, GenerationProgress, QualityReport, RfpDocument } from "@/lib/types";

export default function DraftWorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const [rfpId, setRfpId] = useState<number | null>(null);
  const [rfp, setRfp] = useState<RfpDocument | null>(null);
  const [sections, setSections] = useState<DraftSection[]>([]);
  const [quality, setQuality] = useState<QualityReport | null>(null);
  const [exportResult, setExportResult] = useState<ExportDocxResponse | null>(null);
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [confirmExport, setConfirmExport] = useState(false);
  const [clock, setClock] = useState(Date.now());

  useEffect(() => {
    params.then((value) => setRfpId(Number(value.id)));
  }, [params]);

  useEffect(() => {
    if (rfpId) refresh(rfpId);
  }, [rfpId]);

  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 15000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!rfpId || !["running", "queued"].includes(progress?.status ?? "")) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getGenerationProgress(rfpId);
        setProgress(next);
        if (next.status === "completed" || next.status === "failed" || next.status === "failed_partial" || next.status === "failed_stale") {
          window.clearInterval(timer);
          await refresh(rfpId);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not refresh draft progress.");
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [rfpId, progress?.status]);

  async function refresh(id = rfpId) {
    if (!id) return;
    setLoading("loading");
    try {
      const [rfpData, draftData, qualityData, progressData] = await Promise.all([getRfp(id), getDraft(id), getQuality(id), getGenerationProgress(id)]);
      setRfp(rfpData);
      setSections(draftData);
      setQuality(qualityData);
      setProgress(progressData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the draft workspace.");
    } finally {
      setLoading("");
    }
  }

  async function startGeneration() {
    if (!rfpId) return;
    setConfirm(false);
    setLoading("generating");
    try {
      setProgress({
        rfp_id: rfpId,
        job_id: null,
        status: "running",
        current_step: 0,
        total_steps: 8,
        current_section: "Starting local draft generation...",
        progress_percent: 0,
        external_api_used: false,
        elapsed_seconds: 0,
        estimated_total_seconds: null,
        estimated_remaining_seconds: null,
        average_seconds_per_section: null,
        model_used: null,
      });
      const result = await generateShortDraft(rfpId, true);
      const partialMessage =
        result.status === "failed_partial"
          ? result.error || "Partial draft generated. Review the completed sections and retry to fill the missing part."
          : null;
      setProgress(await getGenerationProgress(rfpId));
      await refresh(rfpId);
      if (partialMessage) {
        setError(partialMessage);
      }
    } catch (err) {
      setError(formatDraftFailureMessage(err));
      setProgress(await getGenerationProgress(rfpId));
      await refresh(rfpId);
    } finally {
      setLoading("");
    }
  }

  async function runQuality() {
    if (!rfpId) return;
    setLoading("quality");
    try {
      setQuality(await getQuality(rfpId));
    } finally {
      setLoading("");
    }
  }

  async function onExport() {
    if (!rfpId) return;
    setConfirmExport(false);
    setLoading("exporting");
    try {
      setExportResult(await exportDocx(rfpId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Word export failed.");
    } finally {
      setLoading("");
    }
  }

  const completion = useMemo(() => progress?.progress_percent ?? 0, [progress]);
  const completedCount = sections.length;
  const isRunning = progress?.status === "running" || progress?.status === "queued";
  const draftReady = sections.length === 8 && progress?.status === "completed";
  const hasInvalidSection = sections.some((section) => section.has_infrastructure_error);
  const canExport = draftReady && completedCount === 8 && !hasInvalidSection && !isRunning;
  const workspaceStatus = progress?.status || "not_started";
  const progressStartedAt = progress?.started_at ? new Date(progress.started_at).getTime() : null;
  const progressUpdatedAt = progress?.updated_at ? new Date(progress.updated_at).getTime() : null;
  const runningElapsedSeconds = progressStartedAt ? Math.max(0, Math.floor((clock - progressStartedAt) / 1000)) : null;
  const progressAgeSeconds = progressUpdatedAt ? Math.max(0, Math.floor((clock - progressUpdatedAt) / 1000)) : null;
  const isStartingSlowly = isRunning && (progress?.current_step ?? 0) === 0 && (runningElapsedSeconds ?? 0) > 60;
  const isStaleRunning = isRunning && (progressAgeSeconds ?? 0) > 180;
  const generationFinished = draftReady;
  const generateDisabled = Boolean(loading) || isRunning || generationFinished;
  const generateLabel = loading === "generating" || isRunning ? "Generating..." : progress?.status === "failed_stale" ? "Retry Generation" : generationFinished ? "Draft Ready" : "Generate Draft";
  const progressFailureMessage = formatDraftFailureMessage(progress?.error_message || progress?.status);

  return (
    <>
      <PageHeader
        title="Draft Workspace"
        description="Generate and review a draft before exporting to Word."
        action={
          <div className="flex flex-wrap gap-2">
              <StatusBadge value={draftReady ? "draft_generated" : workspaceStatus} />
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">Local Only</span>
            </div>
        }
      />

      {error ? <div className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}

      <Card className="mb-6">
        <CardBody>
              <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-lg font-semibold text-slate-950">{rfp?.probable_title || rfp?.title || `RFP ${rfpId ?? ""}`}</div>
              <div className="mt-1 text-sm text-slate-500">Local generation. Human review required.</div>
            </div>
            <div className="flex flex-wrap gap-2">
              <ActionButton variant="primary" onClick={() => setConfirm(true)} disabled={generateDisabled}>
                {generateLabel}
              </ActionButton>
              <ActionButton onClick={runQuality} disabled={Boolean(loading) || isRunning}>
                Review Checks
              </ActionButton>
              <ActionButton onClick={() => setConfirmExport(true)} disabled={Boolean(loading) || !canExport}>
                Export Word Document
              </ActionButton>
              {rfpId && exportResult ? (
                <a className="inline-flex h-9 items-center rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-800" href={downloadDocx(rfpId)}>
                  Download Word Document
                </a>
              ) : null}
            </div>
          </div>
        </CardBody>
      </Card>

      <Card className="mb-6">
        <CardHeader title="Generation Progress" subtitle="Large RFPs can take 15-30 minutes on CPU. This page updates while the draft is being built." />
        <CardBody>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-950">{progress?.current_section || "Waiting to start"}</div>
              <div className="mt-1 text-sm text-slate-500">
                {progress?.status === "failed_stale"
                  ? "Generation was interrupted. You can try again."
                  : isStartingSlowly
                    ? "Starting local draft generation. The first section may take a few minutes."
                    : isStaleRunning
                      ? "No recent progress update. The local engine may be busy. Please wait or check the local engine."
                      : isRunning
                        ? "Still running locally. Large RFPs can take 15-30 minutes on CPU."
                    : "Local generation may take a little longer, but your data stays private."}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <StatusBadge value={progress?.status || "not_started"} />
              <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 font-semibold text-slate-600">
                Local engine
              </span>
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-semibold text-emerald-700">Local only</span>
            </div>
          </div>
          <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-slate-950 transition-all" style={{ width: `${completion}%` }} />
          </div>
          <div className="mt-3 grid gap-3 text-sm text-slate-600 md:grid-cols-2 xl:grid-cols-4">
              <Stat label="Sections complete" value={`${completedCount}/8`} />
            <Stat label="Elapsed" value={formatSeconds(runningElapsedSeconds ?? progress?.elapsed_seconds)} />
            <Stat label="Remaining" value={formatRemaining(progress?.estimated_remaining_seconds)} />
            <Stat label="ETA" value={formatRemaining(progress?.estimated_total_seconds)} />
          </div>
          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {progress?.status === "failed_stale"
              ? progressFailureMessage || "Generation was interrupted after a restart or long pause. Try again to continue."
              : progress?.status === "failed" || progress?.status === "failed_partial"
                ? progressFailureMessage || "Draft generation failed locally. The local engine likely timed out."
              : progress?.status === "completed"
                ? "Draft complete."
                : progress?.estimated_remaining_seconds == null
                  ? "Estimating after the first section..."
                  : `Average time per section: ${formatSeconds(progress.average_seconds_per_section)}.`}
          </div>
        </CardBody>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <section className="space-y-4">
          {sections.length === 0 ? (
            <EmptyState
              title={progress?.status === "failed_stale" ? "Draft interrupted" : "No draft yet"}
              detail={
                progress?.status === "failed_stale"
                  ? progressFailureMessage || "Generation was interrupted. You can try again to continue locally."
                  : progress?.status === "failed" || progress?.status === "failed_partial"
                    ? progressFailureMessage || "Draft generation failed locally."
                  : "Generate a first draft using the document and the local assistant."
              }
              action={
                <ActionButton variant="primary" onClick={() => setConfirm(true)} disabled={generateDisabled}>
                  {generateLabel}
                </ActionButton>
              }
            />
          ) : null}
          {sections.map((section) => (
            <details key={section.id} open={section.section_order === 1} className="rounded-[20px] border border-slate-200 bg-white shadow-sm">
              <summary className="cursor-pointer list-none px-6 py-5">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 text-sm font-semibold text-white">{section.section_order}</span>
                    <div>
                      <h2 className="text-base font-semibold text-slate-950">{section.section_title}</h2>
                      <div className="mt-1 text-xs text-slate-500">{section.word_count} words</div>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {section.has_infrastructure_error ? <span className="rounded-full border border-rose-200 bg-rose-50 px-2 py-1 text-rose-700">Needs review</span> : null}
                    <span>Section {section.section_order}</span>
                  </div>
                </div>
              </summary>
              <div className="border-t border-slate-100 px-6 py-5">
                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{section.section_content}</p>
                {section.has_infrastructure_error ? (
                  <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                    This section needs review before export.
                  </div>
                ) : null}
              </div>
            </details>
          ))}
        </section>

        <aside className="space-y-6 xl:sticky xl:top-24 xl:self-start">
          <Card>
            <CardHeader title="Review Checks" subtitle="Simple checks, not final approval." />
            <CardBody>
              {quality ? (
                <div className="space-y-3">
                  <StatusBadge value={quality.overall_status} />
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800">Human review is still required before submission.</div>
                  {quality.checks.map((check, index) => (
                    <div key={`${check.name}-${index}`} className="rounded-2xl bg-slate-50 p-4 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-semibold text-slate-950">{check.name.replaceAll("_", " ")}</div>
                        <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-semibold text-slate-600">{friendlyCheckStatus(check.status)}</span>
                      </div>
                      <p className="mt-2 leading-6 text-slate-600">{check.message}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No review checks yet.</p>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Export Status" subtitle="Word export is enabled only after a valid completed draft." />
            <CardBody>
              {exportResult ? (
                <div className="space-y-3 text-sm">
                  <div className="rounded-2xl bg-slate-50 p-3">
                    <div className="text-xs uppercase tracking-wide text-slate-500">File</div>
                    <div className="mt-1 truncate font-semibold text-slate-950">{exportResult.file_name}</div>
                  </div>
                  <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 font-semibold text-emerald-800">Generated locally. No external AI provider was used.</div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Export details appear after the draft is ready.</p>
              )}
            </CardBody>
          </Card>
        </aside>
      </div>

      <ConfirmModal
        open={confirm}
        title="Start Local Draft Generation?"
        text="This runs locally. It may take 15-30 minutes on CPU. No external AI provider will be used."
        confirmLabel="Start Generation"
        onCancel={() => setConfirm(false)}
        onConfirm={startGeneration}
      />
      <ConfirmModal
        open={confirmExport}
        title="Export Word Document?"
        text="This runs locally. It will only complete when the draft is ready."
        confirmLabel="Export Word Document"
        onCancel={() => setConfirmExport(false)}
        onConfirm={onExport}
      />
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function formatSeconds(value?: number | null) {
  if (value == null) return "Estimating...";
  if (value < 60) return `${Math.round(value)}s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
}

function formatRemaining(value?: number | null) {
  if (value == null) return "Estimating after the first section...";
  return formatSeconds(value);
}

function friendlyCheckStatus(value: string) {
  const labels: Record<string, string> = {
    pass: "Pass",
    fail: "Needs Attention",
    warning: "Review",
    info: "Info",
  };

  return labels[value] ?? value.replaceAll("_", " ");
}

function formatDraftFailureMessage(err?: unknown): string {
  const raw =
    err instanceof Error
      ? err.message
      : typeof err === "string"
        ? err
        : "";
  const message = raw.toLowerCase();
  if (!message) return "Draft generation failed locally.";
  if (message.includes("timed out") || message.includes("timeout")) {
    return "Draft generation timed out because the local AI engine took too long to respond. Try again after restarting Ollama or using a smaller/faster local model.";
  }
  if (message.includes("busy")) {
    return "Draft generation could not start because the local AI engine is busy. Wait a moment and try again.";
  }
  if (message.includes("offline") || message.includes("not running")) {
    return "Draft generation failed because Ollama is offline. Start Ollama and try again.";
  }
  return raw || "Draft generation failed locally.";
}
