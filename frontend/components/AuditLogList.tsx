import { labelForAuditAction, humanize } from "@/lib/ui-labels";
import type { AuditLog } from "@/lib/types";

function sourceLabel(source: string | null) {
  if (!source) return "System";
  const labels: Record<string, string> = {
    frontend: "App",
    backend: "Local Engine",
    mcp: "Tool Layer",
    system: "System",
  };
  return labels[source] ?? humanize(source);
}

export function AuditLogList({ logs }: { logs: AuditLog[] }) {
  if (logs.length === 0) {
    return <p className="text-sm text-slate-500">No activity yet.</p>;
  }

  return (
    <div className="space-y-3">
      {logs.map((log) => (
        <div key={log.id} className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="font-semibold text-slate-950">{labelForAuditAction(log.action)}</div>
              <div className="mt-1 text-xs text-slate-500">
                {sourceLabel(log.source)} · {new Date(log.created_at).toLocaleString()}
              </div>
            </div>
            <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${log.external_api_used ? "border-rose-200 bg-rose-50 text-rose-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
              {log.external_api_used ? "External AI used" : "Local only"}
            </span>
          </div>
          {log.details_json ? (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-semibold text-slate-500">View details</summary>
              <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-600">{log.details_json}</pre>
            </details>
          ) : null}
        </div>
      ))}
    </div>
  );
}
