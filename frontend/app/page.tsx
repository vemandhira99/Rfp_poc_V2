"use client";

import { useEffect, useMemo, useState } from "react";
import { ActionButton, ActionLink } from "@/components/ActionButton";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { MetricCard } from "@/components/MetricCard";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { embedRfp, getDraft, getOllamaStatus, getUsageSummary, listRfps } from "@/lib/api";
import type { OllamaStatus, RfpDocument, UsageSummary } from "@/lib/types";

export default function HomePage() {
  const [rfps, setRfps] = useState<RfpDocument[]>([]);
  const [draftCounts, setDraftCounts] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [status, setStatus] = useState<OllamaStatus | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [items, usageSummary, engineStatus] = await Promise.all([listRfps(), getUsageSummary(), getOllamaStatus()]);
      setRfps(items);
      setUsage(usageSummary);
      setStatus(engineStatus);
      const counts: Record<number, number> = {};
      await Promise.all(
        items.map(async (rfp) => {
          try {
            counts[rfp.id] = (await getDraft(rfp.id)).length;
          } catch {
            counts[rfp.id] = 0;
          }
        }),
      );
      setDraftCounts(counts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const stats = useMemo(
    () => ({
      total: rfps.length,
      ready: rfps.filter((rfp) => rfp.status === "ready_for_private_chat" || rfp.status === "draft_generated").length,
      needsAttention: rfps.filter((rfp) => rfp.status === "needs_more_detail" || rfp.status === "extraction_needs_review").length,
      drafts: Object.values(draftCounts).filter((count) => count > 0).length,
    }),
    [rfps, draftCounts],
  );

  async function onPrepare(id: number) {
    setBusyId(id);
    try {
      await embedRfp(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preparing for chat failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Private RFP Workspace"
        description="Upload an RFP, review it, ask questions, and generate a draft locally."
        action={<ActionLink href="/upload" variant="primary">Upload New RFP</ActionLink>}
      />

      <Card className="mb-6 overflow-hidden">
        <CardBody className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
          <div className="space-y-4">
            <div className="inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
              Private local workspace
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-slate-950">Your documents, search, chat, drafts, and exports stay on this machine.</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                This workspace is designed for proposal managers, solution architects, and leadership reviews. It keeps the process simple and private.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <ActionLink href="/upload" variant="primary">Upload New RFP</ActionLink>
              <ActionLink href="/settings">View Private Mode</ActionLink>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <InfoPill label="Local engine" value={status?.available ? "Online" : "Offline"} tone={status?.available ? "green" : "red"} />
            <InfoPill label="External services" value="Disabled" tone="green" />
            <InfoPill label="Data Location" value="Local" tone="slate" />
          </div>
        </CardBody>
      </Card>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total RFPs" value={stats.total} helper="Documents uploaded" />
        <MetricCard label="Ready for Review" value={stats.ready} helper="Ready to chat or draft" tone="green" />
        <MetricCard label="Needs Attention" value={stats.needsAttention} helper="Needs a better document" tone="amber" />
        <MetricCard label="Drafts Ready" value={stats.drafts} helper="Ready for review" tone="indigo" />
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Local Activity" value={usage?.local_ai_calls ?? 0} helper="No paid API usage" />
        <MetricCard label="Estimated Usage" value={usage?.estimated_total_tokens ?? 0} helper="For reporting only" tone="green" />
        <MetricCard label="Time Spent Locally" value={formatSeconds(usage?.total_elapsed_seconds)} helper="Processing time on this laptop" tone="indigo" />
        <MetricCard label="External calls" value={usage?.external_ai_calls ?? 0} helper="Should stay at zero" tone="amber" />
      </div>

      <Card>
        <CardHeader
          title="Recent RFPs"
          subtitle="Each row highlights the next best action."
          action={<span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Local Only</span>}
        />
        {loading ? <div className="p-6"><LoadingState label="Loading workspace..." /></div> : null}
        {error ? <div className="m-6 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}
        {!loading && !error && rfps.length === 0 ? (
          <div className="p-6">
            <EmptyState title="No RFPs uploaded" detail="Upload a PDF, DOCX, or TXT file to begin the private workflow." action={<ActionLink href="/upload" variant="primary">Upload New RFP</ActionLink>} />
          </div>
        ) : null}
        {!loading && rfps.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  {["RFP", "Client", "Status", "Document Check", "Draft", "Last Activity", "Next Action"].map((head) => (
                    <th key={head} className="px-4 py-3 font-semibold">
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rfps.map((rfp) => {
                  const next = nextActionForRfp(rfp);
                  return (
                    <tr key={rfp.id} className="h-[82px] hover:bg-slate-50/80">
                      <td className="max-w-[280px] px-4 py-4">
                        <div className="truncate font-semibold text-slate-950">{rfp.probable_title || rfp.title || `RFP ${rfp.id}`}</div>
                        <div className="truncate text-xs text-slate-500">{rfp.original_filename}</div>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-600">{rfp.probable_client || "Not found"}</td>
                      <td className="px-4 py-4">
                        <StatusBadge value={rfp.status} />
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge value={rfp.document_quality} />
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-600">{draftStatusLabel(draftCounts[rfp.id] ?? 0)}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">{new Date(rfp.updated_at).toLocaleDateString()}</td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-2">
                          {next.kind === "prepare" ? (
                            <ActionButton variant="outline" disabled={busyId === rfp.id || isGenerationRunning(rfp)} onClick={() => onPrepare(rfp.id)}>
                              {busyId === rfp.id ? "Preparing..." : isGenerationRunning(rfp) ? "Draft Running" : next.label}
                            </ActionButton>
                          ) : next.kind === "link" ? (
                            <ActionLink href={next.href ?? `/rfps/${rfp.id}`} variant="primary">
                              {next.label}
                            </ActionLink>
                          ) : (
                            <ActionLink href={next.href || `/rfps/${rfp.id}`} variant="primary">
                              {next.label}
                            </ActionLink>
                          )}
                          <ActionLink href={`/rfps/${rfp.id}`} variant="secondary">
                            View
                          </ActionLink>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </>
  );
}

function nextActionForRfp(rfp: RfpDocument): { kind: "prepare" | "link" | "open"; label: string; href?: string } {
  if (isGenerationRunning(rfp)) {
    return { kind: "link", label: "Draft Running", href: `/rfps/${rfp.id}/draft` };
  }
  if (rfp.document_quality === "needs_more_detail" || rfp.document_quality === "insufficient_rfp_detail") {
    return { kind: "link", label: "Upload Better File", href: "/upload" };
  }
  if (rfp.document_quality === "extraction_needs_review") {
    return { kind: "link", label: "Review Document", href: "/upload" };
  }
  if (rfp.embedding_status !== "completed") {
    return { kind: "prepare", label: "Prepare for Chat" };
  }
  if (rfp.status === "draft_generated") {
    return { kind: "link", label: "Open Draft", href: `/rfps/${rfp.id}/draft` };
  }
  if (rfp.status === "ready_for_private_chat") {
    return { kind: "link", label: "Open Chat", href: `/rfps/${rfp.id}` };
  }
  return { kind: "link", label: "Open RFP", href: `/rfps/${rfp.id}` };
}

function isGenerationRunning(rfp: RfpDocument): boolean {
  return rfp.generation_status === "queued" || rfp.generation_status === "running";
}

function InfoPill({ label, value, tone }: { label: string; value: string; tone: "slate" | "green" | "amber" | "red" }) {
  const tones = {
    slate: "border-slate-200 bg-slate-50 text-slate-700",
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    red: "border-rose-200 bg-rose-50 text-rose-700",
  };

  return (
    <div className={`rounded-[20px] border px-4 py-4 ${tones[tone]}`}>
      <div className="text-xs font-semibold uppercase tracking-wide opacity-80">{label}</div>
      <div className="mt-1 text-sm font-semibold">{value}</div>
    </div>
  );
}

function formatSeconds(value?: number | null) {
  if (value == null) return "0s";
  if (value < 60) return `${Math.round(value)}s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes}m ${seconds}s`;
}

function draftStatusLabel(count: number) {
  if (count >= 8) return "Draft Ready";
  if (count > 0) return "In progress";
  return "Not started";
}
