"use client";

import { DragEvent, FormEvent, useState } from "react";
import { ActionButton, ActionLink } from "@/components/ActionButton";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { uploadRfp } from "@/lib/api";
import type { UploadResult } from "@/lib/types";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setResult(null);
    setError(null);
    try {
      setResult(await uploadRfp(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    setFile(event.dataTransfer.files?.[0] ?? null);
  }

  return (
    <>
      <PageHeader title="Upload RFP" description="Add a PDF, DOCX, or TXT file. It stays local on this machine." />
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader title="Document Upload" subtitle="One file, one local check, and a clear result." />
          <CardBody>
            <form onSubmit={onSubmit} className="space-y-5">
              <label
                htmlFor="rfp-file"
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`flex min-h-[340px] cursor-pointer flex-col items-center justify-center rounded-[24px] border border-dashed p-8 text-center transition ${
                  dragging ? "border-slate-400 bg-slate-50" : "border-slate-300 bg-white hover:bg-slate-50"
                }`}
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-950 text-sm font-semibold text-white shadow-lg">RFP</div>
                <div className="mt-5 text-lg font-semibold text-slate-950">Drop your file here</div>
                <div className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                  Supported files: PDF, DOCX, TXT. Reading, checking, and search preparation stay local.
                </div>
                <input id="rfp-file" type="file" accept=".pdf,.docx,.txt" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="sr-only" />
                {file ? (
                  <div className="mt-6 w-full max-w-md rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-left shadow-sm">
                    <div className="truncate text-sm font-semibold text-slate-900">{file.name}</div>
                    <div className="mt-1 text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB selected</div>
                  </div>
                ) : null}
              </label>
              <div className="flex flex-wrap items-center gap-3">
                <ActionButton type="submit" variant="primary" disabled={!file || uploading}>
                  {uploading ? "Uploading and checking..." : "Upload and Check Document"}
                </ActionButton>
                {file ? (
                  <button type="button" onClick={() => setFile(null)} className="text-sm font-semibold text-slate-500 hover:text-slate-900">
                    Clear
                  </button>
                ) : null}
              </div>
              {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}
            </form>
          </CardBody>
        </Card>

        <div className="space-y-6">
          <Card>
          <CardHeader title="Private by design" subtitle="Your document stays on your machine." />
          <CardBody className="space-y-3">
              <PrivacyItem title="Files stay local" text="Uploads, text reading, search, chat, and exports run on this laptop." />
              <PrivacyItem title="No external AI provider" text="No cloud AI services are used." />
              <PrivacyItem title="Human review required" text="The result is a working draft, not a final submission." />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="What happens next" subtitle="The next step is always clear." />
            <CardBody className="space-y-3">
              <WorkflowStep title="Upload" text="Bring in the document." />
              <WorkflowStep title="Check" text="We review the text and explain the result." />
              <WorkflowStep title="Prepare for Chat" text="We prepare the document for grounded answers." />
              <WorkflowStep title="Ask Questions" text="Ask private questions using only local content." />
              <WorkflowStep title="Generate Draft" text="Create an 8-section first draft locally." />
              <WorkflowStep title="Export Word Document" text="Create the Word file only when the draft is valid." />
            </CardBody>
          </Card>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader title="Upload Result" subtitle="A plain-language summary of what was found." />
          <CardBody>
            {!result ? (
              <p className="text-sm text-slate-500">Results appear here after upload.</p>
            ) : (
              <div className="space-y-5">
                <ResultMessage result={result} />
                <div className="grid gap-3 text-sm md:grid-cols-2">
                  <Info label="Document" value={String(result.rfp_id)} />
                  <Info label="File" value={result.original_filename} />
                  <Info label="Pages" value={String(result.page_count)} />
                  <Info label="Words" value={result.word_count.toLocaleString()} />
                  <Info label="Sections" value={String(result.chunk_count)} />
                  <Info label="Status" value={friendlyResultStatus(result.status)} />
                </div>
                <div className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2">
                  <Info label="Client" value={result.probable_client || "Not found"} />
                  <Info label="Deadline" value={result.probable_deadline || "Not found"} />
                </div>
                <div className="rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">{result.reason}</div>
                {result.extracted_text_preview ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Text preview</div>
                    <p className="whitespace-pre-wrap">{result.extracted_text_preview}</p>
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-3">
                  <ActionLink href={`/rfps/${result.rfp_id}`} variant="primary">
                    Open Workspace
                  </ActionLink>
                  <ActionLink href="/upload">Upload Another File</ActionLink>
                </div>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Document Check" subtitle="The readiness result uses simple, plain wording." />
          <CardBody className="space-y-3">
            <CheckItem value="Ready" text="Your document is ready. You can prepare it for private chat." tone="green" />
            <CheckItem value="Text Extraction Issue" text="We found pages, but very little readable text. This may be a scanned PDF." tone="amber" />
            <CheckItem value="Needs Better Document" text="This file does not contain enough RFP detail." tone="red" />
          </CardBody>
        </Card>
      </div>
    </>
  );
}

function ResultMessage({ result }: { result: UploadResult }) {
  if (result.document_quality === "insufficient_rfp_detail") {
    return <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800">This file does not contain enough RFP detail.</div>;
  }
  if (result.document_quality === "extraction_needs_review") {
    return <div className="rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm font-semibold text-orange-800">We found pages, but very little readable text. This may be a scanned PDF.</div>;
  }
  return <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">Your document is ready. You can prepare it for private chat.</div>;
}

function friendlyResultStatus(value: string) {
  const labels: Record<string, string> = {
    ready_for_private_chat: "Ready",
    valid_rfp: "Ready",
    limited_but_valid: "Ready",
    needs_more_detail: "Needs Better Document",
    insufficient_rfp_detail: "Needs Better Document",
    extraction_needs_review: "Text Extraction Issue",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 break-words text-sm font-semibold text-slate-950">{value}</div>
    </div>
  );
}

function WorkflowStep({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-sm font-semibold text-slate-950">{title}</div>
      <p className="mt-1 text-sm leading-6 text-slate-500">{text}</p>
    </div>
  );
}

function PrivacyItem({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-sm font-semibold text-slate-950">{title}</div>
      <p className="mt-1 text-sm leading-6 text-slate-500">{text}</p>
    </div>
  );
}

function CheckItem({ value, text, tone }: { value: string; text: string; tone: "green" | "amber" | "red" }) {
  const classes = {
    green: "border-emerald-200 bg-emerald-50 text-emerald-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    red: "border-rose-200 bg-rose-50 text-rose-800",
  };
  return (
    <div className={`rounded-2xl border p-4 ${classes[tone]}`}>
      <div className="text-sm font-semibold">{value}</div>
      <p className="mt-1 text-sm leading-6 opacity-90">{text}</p>
    </div>
  );
}
