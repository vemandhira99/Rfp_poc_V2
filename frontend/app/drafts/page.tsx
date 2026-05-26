"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { Card, CardBody } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { getDraft, listRfps } from "@/lib/api";
import type { RfpDocument } from "@/lib/types";

type DraftRow = RfpDocument & { draft_count: number };

export default function DraftsPage() {
  const [rows, setRows] = useState<DraftRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const rfps = await listRfps();
      const enriched = await Promise.all(
        rfps.map(async (rfp) => {
          try {
            return { ...rfp, draft_count: (await getDraft(rfp.id)).length };
          } catch {
            return { ...rfp, draft_count: 0 };
          }
        }),
      );
      setRows(enriched);
      setLoading(false);
    }
    load();
  }, []);

  return (
    <>
      <PageHeader title="Drafts" description="Open a draft workspace or generate a private short draft for an RFP." />
      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">Loading drafts...</div> : null}
      {!loading && rows.length === 0 ? <EmptyState title="No RFPs available" detail="Upload an RFP before generating drafts." /> : null}
      <div className="grid gap-3">
        {rows.map((rfp) => (
          <Link key={rfp.id} href={`/rfps/${rfp.id}/draft`}>
            <Card className="transition hover:bg-slate-50">
              <CardBody>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-950">{rfp.probable_title || rfp.title || `RFP ${rfp.id}`}</div>
                    <div className="mt-1 text-sm text-slate-500">{rfp.original_filename}</div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge value={rfp.draft_count === 8 ? "draft_generated" : "not_started"} />
                    <span className="text-sm text-slate-500">{rfp.draft_count}/8 sections</span>
                  </div>
                </div>
              </CardBody>
            </Card>
          </Link>
        ))}
      </div>
    </>
  );
}
