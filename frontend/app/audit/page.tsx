"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { AuditLogList } from "@/components/AuditLogList";
import type { AuditLog } from "@/lib/types";
import { auditExportUrl, getAuditLogs } from "@/lib/api";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState("");
  const [rfpId, setRfpId] = useState("");
  const [external, setExternal] = useState("");

  useEffect(() => {
    getAuditLogs(100).then(setLogs).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () =>
      logs.filter((log) => {
        if (source && log.source !== source) return false;
        if (rfpId && String(log.rfp_id ?? "") !== rfpId) return false;
        if (external && String(log.external_api_used) !== external) return false;
        return true;
      }),
    [logs, source, rfpId, external],
  );

  const stats = useMemo(
    () => ({
      total: logs.length,
      local: logs.filter((log) => !log.external_api_used).length,
      external: logs.filter((log) => log.external_api_used).length,
      latest: logs[0]?.created_at,
    }),
    [logs],
  );

  return (
    <>
      <PageHeader title="Activity Log" description="Track local actions performed in this workspace." />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Total actions" value={stats.total} helper="Uploads, chat, drafts, exports, and tools" />
        <Stat label="Local actions" value={stats.local} helper="Processed on this machine" />
        <Stat label="External calls" value={stats.external} helper="Should remain at zero" />
        <Stat label="Latest activity" value={stats.latest ? new Date(stats.latest).toLocaleString() : "None yet"} helper="Most recent event" />
      </div>
      <Card>
        <CardHeader
          title="Timeline"
          subtitle="Most recent events first."
          action={
            <a className="rounded-xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white" href={auditExportUrl({ rfpId, limit: 500 })}>
              Export Activity Log
            </a>
          }
        />
        <CardBody>
          <div className="mb-5 grid gap-3 md:grid-cols-3">
            <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="">All sources</option>
              <option value="frontend">App</option>
              <option value="backend">Local system</option>
              <option value="mcp">Tool layer</option>
              <option value="system">System</option>
            </select>
            <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="Filter RFP ID" value={rfpId} onChange={(e) => setRfpId(e.target.value)} />
            <select className="rounded-xl border border-slate-200 px-3 py-2 text-sm" value={external} onChange={(e) => setExternal(e.target.value)}>
              <option value="">All activity</option>
              <option value="false">Local only</option>
              <option value="true">External calls</option>
            </select>
          </div>
          {loading ? <LoadingState label="Loading activity log..." /> : null}
          {!loading && filtered.length === 0 ? <p className="text-sm text-slate-500">No activity matches the current filters.</p> : null}
          <AuditLogList logs={filtered} />
        </CardBody>
      </Card>
    </>
  );
}

function Stat({ label, value, helper }: { label: string; value: number | string; helper: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{helper}</div>
    </div>
  );
}
