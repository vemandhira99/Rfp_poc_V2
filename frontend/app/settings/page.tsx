"use client";

import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { API_BASE_URL, getOllamaStatus, getUsageSummary } from "@/lib/api";
import type { OllamaStatus, UsageSummary } from "@/lib/types";

export default function SettingsPage() {
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOllamaStatus().then(setStatus).catch((err: Error) => setError(err.message));
    getUsageSummary().then(setUsage).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <>
      <PageHeader title="Private Mode Settings" description="Confirm the local runtime, models, and privacy controls." />
      {error ? <div className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Privacy Status" subtitle="The core privacy posture for the workspace." />
          <CardBody className="space-y-4">
            <Setting label="Private Mode" value="Enabled" badge="Local only" />
            <Setting label="External AI Providers" value="Disabled" badge="Blocked" />
            <Setting label="Data Storage" value="Local" />
            <Setting label="Document Processing" value="Local" />
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold leading-6 text-emerald-800">
              Uploaded documents, search preparation, chat, draft generation, and Word export stay on this machine.
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Local AI Engine" subtitle="Single source of truth for local model availability." />
          <CardBody className="space-y-4">
            <Setting label="Runtime" value="Ollama" />
            <Setting label="Local AI Engine URL" value={status?.ollama_base_url ?? "http://localhost:11434"} />
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 p-4">
              <span className="text-sm font-semibold text-slate-600">Availability</span>
              <StatusBadge value={status?.available ? "completed" : "generation_failed"} />
            </div>
            <Setting label="Local Chat Model" value={status?.chat_model ?? "llama3.2:3b"} />
            <Setting label="Local Search Model" value={status?.embedding_model ?? "nomic-embed-text"} />
            <Setting label="Message" value={status?.message ?? "All required local models are available."} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Usage Summary" subtitle="Estimated local usage only. No paid API tokens are consumed." />
          <CardBody className="grid gap-3 sm:grid-cols-2">
            <Metric label="Local calls" value={usage?.local_ai_calls ?? 0} />
            <Metric label="Estimated tokens" value={usage?.estimated_total_tokens ?? 0} />
            <Metric label="Generation time" value={formatSeconds(usage?.total_elapsed_seconds)} />
            <Metric label="External calls" value={usage?.external_ai_calls ?? 0} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Local Control Notes" subtitle="Boundary conditions for the demo." />
          <CardBody className="grid gap-3 sm:grid-cols-2">
            <Note title="Local usage only" text="Every model call is logged locally for observability." />
            <Note title="No paid API tokens consumed" text="Estimated tokens are approximate and for reporting only." />
            <Note title="Draft protection" text="Failed generations are blocked from Word export." />
            <Note title="Ollama required" text="Generation and search preparation stop if the runtime or models are unavailable." />
          </CardBody>
        </Card>
      </div>
    </>
  );
}

function Setting({ label, value, badge }: { label: string; value: string; badge?: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
        {badge ? <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">{badge}</span> : null}
      </div>
      <div className="mt-2 break-words text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function Note({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-sm font-semibold text-slate-950">{title}</div>
      <p className="mt-1 text-sm leading-6 text-slate-500">{text}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-950">{value}</div>
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
