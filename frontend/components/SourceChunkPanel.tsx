import type { SourceChunk } from "@/lib/types";

export function SourceChunkPanel({ chunks }: { chunks: SourceChunk[] }) {
  return (
    <details className="mt-4 rounded-2xl border border-slate-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-800">View source excerpts ({chunks.length})</summary>
      <div className="space-y-3 border-t border-slate-200 p-4">
        {chunks.length === 0 ? <p className="text-sm text-slate-500">No source excerpts returned.</p> : null}
        {chunks.map((chunk) => (
          <div key={chunk.chunk_id} className="rounded-xl bg-slate-50 p-3 text-xs">
            <div className="font-semibold text-slate-900">
              Excerpt {chunk.chunk_id} · {chunk.retrieval_type ?? "retrieval"} · {chunk.score.toFixed(3)}
            </div>
            <p className="mt-2 line-clamp-4 leading-5 text-slate-600">{chunk.preview || chunk.chunk_text}</p>
          </div>
        ))}
      </div>
    </details>
  );
}
