"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Dashboard", icon: "D" },
  { href: "/upload", label: "Upload", icon: "U" },
  { href: "/chat", label: "Review RFP", icon: "R" },
  { href: "/drafts", label: "Drafts", icon: "F" },
  { href: "/audit", label: "Audit", icon: "A" },
  { href: "/settings", label: "Settings", icon: "S" },
];

type SidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
  statusLabel: string;
  statusTone: string;
};

export function Sidebar({ collapsed, onToggle, statusLabel, statusTone }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-20 hidden border-r border-slate-200/80 bg-white/95 backdrop-blur md:flex md:flex-col ${
        collapsed ? "w-[72px] px-3 py-4" : "w-[260px] px-4 py-5"
      }`}
    >
      <div className={`rounded-[20px] bg-slate-950 p-4 text-white shadow-lg ${collapsed ? "text-center" : ""}`}>
        <div className={`flex ${collapsed ? "justify-center" : "items-start gap-3"}`}>
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 text-sm font-bold">PR</div>
          {!collapsed ? (
            <div>
              <div className="text-base font-semibold">Private RFP Tool</div>
              <div className="mt-1 text-xs text-slate-300">Local-first proposal workspace</div>
            </div>
          ) : null}
        </div>
      </div>

      <nav className="mt-5 space-y-1">
        {navItems.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={`group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-semibold transition ${
                active ? "bg-slate-950 text-white shadow-sm" : "text-slate-700 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              <span className={`flex h-8 w-8 items-center justify-center rounded-xl text-xs font-bold transition ${active ? "bg-white/15 text-white" : "bg-slate-100 text-slate-600 group-hover:bg-white"}`}>
                {item.icon}
              </span>
              {!collapsed ? <span>{item.label}</span> : null}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3">
        <div className={`rounded-[20px] border border-emerald-200 bg-emerald-50 p-3 ${collapsed ? "text-center" : ""}`}>
          <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Private Mode</div>
          {!collapsed ? <p className="mt-1 text-xs leading-5 text-emerald-800">Documents stay local. No external AI providers are used.</p> : null}
        </div>
        <div className="rounded-[20px] border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">System</div>
          {!collapsed ? (
            <div className="mt-2 space-y-1 text-xs text-slate-700">
              <div className="flex items-center justify-between gap-3">
                <span>Local AI Engine</span>
                <span className={statusTone}>{statusLabel}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>External AI</span>
                <span className="text-emerald-700">Disabled</span>
              </div>
            </div>
          ) : (
            <div className="mt-2 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-500">{statusLabel}</div>
          )}
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="flex w-full items-center justify-center rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          {collapsed ? "Expand" : "Collapse"}
        </button>
      </div>
    </aside>
  );
}
