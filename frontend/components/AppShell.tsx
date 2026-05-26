"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { getOllamaStatus } from "@/lib/api";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import type { OllamaStatus } from "@/lib/types";

const STORAGE_KEY = "private-rfp-sidebar-collapsed";

const mobileNav = [
  { href: "/", label: "Home" },
  { href: "/upload", label: "Upload" },
  { href: "/chat", label: "Review" },
  { href: "/drafts", label: "Drafts" },
  { href: "/audit", label: "Audit" },
  { href: "/settings", label: "Settings" },
];

const routeLabels: Record<string, string> = {
  "/": "Private RFP Workspace",
  "/upload": "Upload RFP",
  "/chat": "Review RFP",
  "/drafts": "Drafts",
  "/audit": "Activity Log",
  "/settings": "Private Mode Settings",
};

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [status, setStatus] = useState<OllamaStatus | null>(null);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored !== null) {
        setCollapsed(stored === "true");
      }
    } catch {
      // Ignore localStorage failures in private browsing or locked-down environments.
    }
    void refreshStatus();
    const handleRefreshStatus = () => {
      void refreshStatus();
    };
    window.addEventListener("private-rfp:refresh-status", handleRefreshStatus);
    return () => window.removeEventListener("private-rfp:refresh-status", handleRefreshStatus);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(collapsed));
    } catch {
      // Ignore storage failures.
    }
  }, [collapsed]);

  const sidebarWidth = collapsed ? "72px" : "260px";
  const sidebarLabel = !status
    ? "Checking"
    : !status.available
      ? "Offline"
      : !status.chat_model_available
        ? "Chat Missing"
        : !status.embedding_model_available
          ? "Search Missing"
          : "Online";
  const sidebarTone = !status || !status.available
    ? "text-rose-700"
    : !status.chat_model_available || !status.embedding_model_available
      ? "text-amber-700"
      : "text-emerald-700";

  const contextLabel = useMemo(() => {
    if (pathname.startsWith("/rfps/") && pathname.endsWith("/draft")) return "Draft Workspace";
    if (pathname.startsWith("/rfps/")) return "RFP Detail";
    return routeLabels[pathname] ?? "Private RFP Workspace";
  }, [pathname]);

  async function refreshStatus() {
    try {
      setStatus(await getOllamaStatus());
    } catch {
      setStatus(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((current) => !current)}
        statusLabel={sidebarLabel}
        statusTone={sidebarTone}
      />
      <main className="min-h-screen md:transition-[padding] md:duration-300" style={{ paddingLeft: sidebarWidth }}>
        <TopBar status={status} contextLabel={contextLabel} />
        <div className="border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <div className="grid grid-cols-6 gap-1 text-xs">
            {mobileNav.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-xl border border-slate-200 px-2 py-2 text-center font-medium text-slate-700">
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</div>
      </main>
    </div>
  );
}
