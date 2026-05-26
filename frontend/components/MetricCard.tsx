import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  helper,
  icon,
  tone = "slate",
}: {
  label: string;
  value: number | string;
  helper?: string;
  icon?: ReactNode;
  tone?: "slate" | "green" | "amber" | "red" | "indigo";
}) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    red: "bg-rose-50 text-rose-700",
    indigo: "bg-indigo-50 text-indigo-700",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
        {icon ? <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${tones[tone]}`}>{icon}</div> : null}
      </div>
      <div className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">{value}</div>
      {helper ? <div className="mt-1 text-sm text-slate-500">{helper}</div> : null}
    </div>
  );
}
