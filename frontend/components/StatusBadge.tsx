import { friendlyStatusLabel } from "@/lib/ui-labels";

type StatusBadgeProps = {
  value: string;
};

const toneByValue: Record<string, string> = {
  valid_rfp: "border-emerald-200 bg-emerald-50 text-emerald-700",
  limited_but_valid: "border-amber-200 bg-amber-50 text-amber-800",
  insufficient_rfp_detail: "border-rose-200 bg-rose-50 text-rose-700",
  extraction_needs_review: "border-orange-200 bg-orange-50 text-orange-800",
  ready_for_private_chat: "border-emerald-200 bg-emerald-50 text-emerald-700",
  needs_more_detail: "border-amber-200 bg-amber-50 text-amber-800",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  running: "border-slate-200 bg-slate-50 text-slate-700",
  queued: "border-slate-200 bg-slate-50 text-slate-700",
  failed_partial: "border-amber-200 bg-amber-50 text-amber-800",
  not_started: "border-slate-200 bg-slate-50 text-slate-700",
  partial: "border-amber-200 bg-amber-50 text-amber-800",
  not_applicable: "border-slate-200 bg-slate-50 text-slate-700",
  draft_generated: "border-indigo-200 bg-indigo-50 text-indigo-700",
  generation_failed: "border-rose-200 bg-rose-50 text-rose-700",
  failed_stale: "border-amber-200 bg-amber-50 text-amber-800",
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const tone = toneByValue[value] ?? "border-slate-200 bg-slate-50 text-slate-700";
  return <span className={`inline-flex h-7 items-center rounded-full border px-2.5 text-xs font-semibold ${tone}`}>{friendlyStatusLabel(value)}</span>;
}
