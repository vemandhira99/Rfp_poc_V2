"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { Card, CardBody } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { listRfps } from "@/lib/api";
import type { RfpDocument } from "@/lib/types";

export default function ChatIndexPage() {
  const [rfps, setRfps] = useState<RfpDocument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRfps().then(setRfps).finally(() => setLoading(false));
  }, []);

  return (
    <>
      <PageHeader title="Review RFP" description="Choose an uploaded RFP to open its private assistant." />
      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">Loading RFPs...</div> : null}
      {!loading && rfps.length === 0 ? <EmptyState title="No RFPs available" detail="Upload an RFP before opening the private assistant." /> : null}
      <div className="grid gap-3">
        {rfps.map((rfp) => (
          <Link key={rfp.id} href={`/rfps/${rfp.id}`}>
            <Card className="transition hover:bg-slate-50">
              <CardBody>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-950">{rfp.probable_title || rfp.title || `RFP ${rfp.id}`}</div>
                    <div className="mt-1 text-sm text-slate-500">{rfp.original_filename}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge value={rfp.document_quality} />
                    <StatusBadge value={rfp.status} />
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
