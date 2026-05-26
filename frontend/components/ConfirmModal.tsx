"use client";

import { ActionButton } from "./ActionButton";

export function ConfirmModal({ open, title, text, confirmLabel = "Continue", onCancel, onConfirm }: { open: boolean; title: string; text: string; confirmLabel?: string; onCancel: () => void; onConfirm: () => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-md rounded-[20px] border border-slate-200 bg-white p-6 shadow-xl">
        <div className="text-lg font-semibold text-slate-950">{title}</div>
        <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
        <div className="mt-4 inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Local only</div>
        <div className="mt-6 flex justify-end gap-2">
          <ActionButton onClick={onCancel}>Cancel</ActionButton>
          <ActionButton variant="primary" onClick={onConfirm}>{confirmLabel}</ActionButton>
        </div>
      </div>
    </div>
  );
}
