"use client";

import type { OllamaStatus } from "@/lib/types";

type TopBarProps = {
  status: OllamaStatus | null;
  contextLabel: string;
};

function statusLabel(status: OllamaStatus | null) {
  if (!status) return "Checking local engine";
  if (!status.available) return "Local AI Engine Offline";
  if (!status.chat_model_available) return "Chat Model Missing";
  if (!status.embedding_model_available) return "Search Model Missing";
  return "Local AI Engine Online";
}

function statusTone(status: OllamaStatus | null) {
  if (!status || !status.available) return "border-rose-200 bg-rose-50 text-rose-700";
  if (!status.chat_model_available || !status.embedding_model_available) return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-emerald-200 bg-emerald-50 text-emerald-800";
}

export function TopBar({ status, contextLabel }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/90 px-5 py-3 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-950">{contextLabel}</div>
          <div className="text-xs text-slate-500">Your document stays on this machine.</div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-700">Local Only</span>
          <span className={`rounded-full border px-2.5 py-1 font-semibold ${statusTone(status)}`}>{statusLabel(status)}</span>
          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-600">Private Mode</span>
        </div>
      </div>
    </header>
  );
}
