"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ActionButton } from "@/components/ActionButton";
import { Card, CardBody, CardHeader } from "@/components/Card";
import { SourceChunkPanel } from "@/components/SourceChunkPanel";
import { chatWithRfp, getChatHistory } from "@/lib/api";
import type { ChatHistoryItem, SourceChunk } from "@/lib/types";

type PrivateChatPanelProps = {
  rfpId: number;
  inputId?: string;
};

const SUGGESTIONS = [
  "Summarize this RFP",
  "What are the key requirements?",
  "What are the main risks?",
  "What is the deadline?",
  "Explain compliance requirements",
  "What should the proposal focus on?",
];

type ChatBubble = {
  role: "user" | "assistant";
  message: string;
  provider?: string | null;
  model_used?: string | null;
  retrieval_mode?: string | null;
  external_api_used?: boolean;
  source_chunks?: SourceChunk[];
  intent?: string | null;
  code?: string | null;
  client_message_id?: string | null;
  local_order?: number;
  created_at?: string;
};

const LOCAL_ENGINE_OFFLINE_CODE = "LOCAL_ENGINE_OFFLINE";
const LOCAL_ENGINE_TIMEOUT_CODE = "LOCAL_ENGINE_TIMEOUT";
const LOCAL_ENGINE_BUSY_CODE = "LOCAL_ENGINE_BUSY";
const LOCAL_ENGINE_ERROR_CODE = "LOCAL_ENGINE_ERROR";
const LOCAL_MODEL_MISSING_CODE = "LOCAL_MODEL_MISSING";

export function PrivateChatPanel({ rfpId, inputId = "private-chat-input" }: PrivateChatPanelProps) {
  const [items, setItems] = useState<ChatBubble[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const pendingRef = useRef<number | null>(null);
  const localOrderRef = useRef(0);
  const historyLoadedRef = useRef(false);
  const historySeqRef = useRef(0);

  useEffect(() => {
    historyLoadedRef.current = false;
    void loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rfpId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items.length, loading]);

  async function loadHistory() {
    const seq = ++historySeqRef.current;
    try {
      const history = await getChatHistory(rfpId, 20);
      if (seq !== historySeqRef.current) return;
      setItems(normalizeHistory(history.flatMap(toBubble)));
      setError(null);
    } catch {
      if (seq !== historySeqRef.current) return;
      setError("Could not load recent chat history.");
    }
  }

  function toBubble(item: ChatHistoryItem): ChatBubble[] {
    if (item.role === "assistant") {
      const sourceChunks = parseSourceChunks(item.source_chunks_json);
      return [
        {
          role: "assistant",
          message: item.message,
          provider: item.provider,
          model_used: item.model_used,
          retrieval_mode: sourceChunks.length > 0 ? "Smart Local Search" : "Local",
          external_api_used: false,
          source_chunks: sourceChunks,
          intent: item.intent,
          created_at: item.created_at,
          local_order: ++localOrderRef.current,
        },
      ];
    }
    return [{ role: "user", message: item.message, created_at: item.created_at, local_order: ++localOrderRef.current }];
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendQuestion(question);
  }

  async function sendQuestion(rawQuestion: string) {
    const trimmed = rawQuestion.trim();
    if (!trimmed || loading) return;
    setQuestion("");
    setLoading(true);
    setError(null);
    const tempId = Date.now();
    pendingRef.current = tempId;
    const turnId = `client-${tempId}`;
    const createdAt = new Date().toISOString();
    setItems((existing) => [...existing, { role: "user", message: trimmed, client_message_id: turnId, local_order: ++localOrderRef.current, created_at: createdAt }]);
    try {
      const response = await chatWithRfp(rfpId, trimmed);
      if (pendingRef.current !== tempId) return;
      setItems((existing) => {
        const next = [...existing];
        next.push({
          role: "assistant",
          message: response.answer,
          provider: response.provider,
          model_used: response.model_used,
          retrieval_mode: response.retrieval_mode,
          external_api_used: response.external_api_used,
          source_chunks: response.source_chunks,
          intent: response.intent,
          code: response.code,
          client_message_id: turnId,
          local_order: ++localOrderRef.current,
          created_at: new Date().toISOString(),
        });
        return normalizeHistory(next);
      });
      if (response.code && response.code !== "LOCAL_ENGINE_ERROR") {
        window.dispatchEvent(new Event("private-rfp:refresh-status"));
      }
    } catch {
      window.dispatchEvent(new Event("private-rfp:refresh-status"));
      setError("Local AI Engine is offline. Start the local engine and try again.");
    } finally {
      pendingRef.current = null;
      setLoading(false);
    }
  }

  function onSuggestion(text: string) {
    void sendQuestion(text);
  }

  return (
    <Card className="min-h-[640px]">
      <CardHeader
        title="Private RFP Assistant"
        subtitle="Ask questions about this RFP. Answers are generated locally from document excerpts."
        action={
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-700">Local Only</span>
          </div>
        }
      />
      <CardBody>
        <div className="mb-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => onSuggestion(suggestion)}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
        {error ? <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{error}</div> : null}
        <div className="mb-5 h-[430px] overflow-y-auto rounded-[24px] bg-slate-50 p-4">
          {items.length === 0 && !loading ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">Ask a question to start a private local chat.</div>
          ) : null}
          <div className="space-y-5">
            {items.map((item, index) => (
              <ChatRow key={`${item.role}-${index}-${item.created_at ?? index}`} item={item} />
            ))}
            {loading ? <TypingBubble /> : null}
            <div ref={scrollRef} />
          </div>
        </div>
        <form id={`private-chat-form-${rfpId}`} onSubmit={onSubmit} className="space-y-3">
          <textarea
            id={inputId}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            className="min-h-[96px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-slate-400"
            placeholder="Ask about scope, requirements, dates, risks..."
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-600">Local Only</span>
            </div>
            <ActionButton type="submit" variant="primary" disabled={!question.trim() || loading}>
              {loading ? "Thinking locally..." : "Send"}
            </ActionButton>
          </div>
        </form>
      </CardBody>
    </Card>
  );
}

function parseSourceChunks(raw?: string | null): SourceChunk[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((chunk) => ({
      chunk_id: Number(chunk.chunk_id),
      chunk_order: Number(chunk.chunk_order),
      section_title: chunk.section_title ?? null,
      page_number: chunk.page_number ?? null,
      score: Number(chunk.score ?? 0),
      retrieval_type: chunk.retrieval_type ?? null,
      chunk_text: chunk.chunk_text ?? "",
      preview: chunk.preview ?? chunk.chunk_text ?? "",
    }));
  } catch {
    return [];
  }
}

function ChatRow({ item }: { item: ChatBubble }) {
  if (item.role === "user") {
    return (
      <div className="ml-auto max-w-[80%] rounded-3xl rounded-br-lg bg-slate-950 px-4 py-3 text-sm leading-6 text-white shadow-sm">
        {item.message}
      </div>
    );
  }

  const errorCodeSet = new Set([LOCAL_ENGINE_OFFLINE_CODE, LOCAL_ENGINE_BUSY_CODE, LOCAL_ENGINE_ERROR_CODE, LOCAL_ENGINE_TIMEOUT_CODE, LOCAL_MODEL_MISSING_CODE]);
  const errorCode = item.code && errorCodeSet.has(item.code) ? item.code : null;
  const showSourceBadges = item.provider === "local_ollama" && (item.source_chunks?.length ?? 0) > 0 && !errorCode;
  const showDetails = item.provider === "local_ollama" && showSourceBadges;
  return (
    <div className="max-w-[86%]">
      <div className="flex items-start gap-3">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl text-sm font-bold text-white ${errorCode ? "bg-amber-600" : "bg-slate-800"}`}>AI</div>
        <div className={`w-full rounded-3xl rounded-tl-lg border px-4 py-3 shadow-sm ${errorCode ? "border-amber-200 bg-amber-50" : "border-slate-200 bg-white"}`}>
          {errorCode ? (
            <div className="mb-3 rounded-2xl border border-amber-200 bg-white/80 p-3 text-sm text-amber-900">
              <div className="font-semibold">{warningTitleForCode(errorCode)}</div>
              <div className="mt-1">{warningMessageForCode(errorCode)}</div>
            </div>
          ) : null}
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{item.message}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-600">Local Only</span>
            {showSourceBadges ? (
              <>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-600">Smart Local Search</span>
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-semibold text-emerald-700">Sources used</span>
              </>
            ) : null}
          </div>
          {showDetails ? (
            <details className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <summary className="cursor-pointer text-xs font-semibold text-slate-700">Details</summary>
              <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
                <Meta label="Provider" value={item.provider || "local"} />
                <Meta label="Model" value={item.model_used || "Local Chat Model"} />
                <Meta label="Retrieval" value={item.retrieval_mode || "Local"} />
                <Meta label="Intent" value={item.intent || "rfp_question"} />
              </div>
            </details>
          ) : null}
          {showSourceBadges && item.source_chunks && item.source_chunks.length > 0 ? <SourceChunkPanel chunks={item.source_chunks} /> : null}
        </div>
      </div>
    </div>
  );
}

function warningTitleForCode(code: string) {
  if (code === LOCAL_ENGINE_BUSY_CODE) return "Local AI Engine is busy";
  if (code === LOCAL_ENGINE_TIMEOUT_CODE) return "Local AI Engine timed out";
  if (code === LOCAL_MODEL_MISSING_CODE) return "Local model is missing";
  if (code === LOCAL_ENGINE_ERROR_CODE) return "Local AI Engine had an error";
  return "Local AI Engine is offline";
}

function warningMessageForCode(code: string) {
  if (code === LOCAL_ENGINE_BUSY_CODE) return "Please try again in a moment.";
  if (code === LOCAL_ENGINE_TIMEOUT_CODE) return "The local AI engine took too long to respond. Try again in a moment.";
  if (code === LOCAL_MODEL_MISSING_CODE) return "Pull the required local model and try again.";
  if (code === LOCAL_ENGINE_ERROR_CODE) return "Please try again in a moment.";
  return "Start the local engine and try again.";
}

function normalizeHistory(items: ChatBubble[]): ChatBubble[] {
  const seen = new Set<string>();
  const filtered = items.filter((item) => {
    const key = `${item.role}|${item.client_message_id ?? ""}|${item.message}|${item.created_at ?? ""}|${item.provider ?? ""}|${item.intent ?? ""}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return filtered.sort((left, right) => {
    const leftTime = left.created_at ? new Date(left.created_at).getTime() : 0;
    const rightTime = right.created_at ? new Date(right.created_at).getTime() : 0;
    if (leftTime !== rightTime) return leftTime - rightTime;
    return (left.local_order ?? 0) - (right.local_order ?? 0);
  });
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white px-3 py-2">
      <div className="font-semibold text-slate-500">{label}</div>
      <div className="mt-1 break-words text-slate-800">{value}</div>
    </div>
  );
}

function TypingBubble() {
  return (
    <div className="max-w-[86%]">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-slate-800 text-sm font-bold text-white">AI</div>
        <div className="rounded-3xl rounded-tl-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="text-sm font-semibold text-slate-700">Private assistant is thinking locally...</div>
          <div className="mt-2 flex items-center gap-1">
            <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400" />
            <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:120ms]" />
            <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400 [animation-delay:240ms]" />
          </div>
        </div>
      </div>
    </div>
  );
}
