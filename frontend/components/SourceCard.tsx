import type { RetrievalEvent } from "@/lib/api";

const SCORE_LABELS: { key: keyof RetrievalEvent["scores"]; label: string; color: string }[] = [
  { key: "bm25", label: "lex", color: "bg-amber" },
  { key: "vector", label: "vec", color: "bg-teal" },
  { key: "hybrid", label: "hyb", color: "bg-text-muted" },
  { key: "rerank", label: "rrk", color: "bg-text" },
];

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-text-dim">
      <span className="w-6 uppercase tracking-wide">{label}</span>
      <span className="h-1.5 w-10 bg-panel-raised overflow-hidden">
        <span className={`block h-full ${color}`} style={{ width: `${pct}%` }} />
      </span>
    </div>
  );
}

export function SourceCard({ event, index }: { event: RetrievalEvent; index: number }) {
  return (
    <div
      className="card-enter border border-border bg-panel px-3 py-2.5"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <p className="text-amber text-sm truncate">
          <span className="text-text-dim">[{index + 1}]</span> @@ {event.file_path} @@
        </p>
        <div className="flex gap-3 shrink-0">
          {SCORE_LABELS.map(({ key, label, color }) => (
            <ScoreBar key={key} label={label} value={event.scores[key]} color={color} />
          ))}
        </div>
      </div>
      <pre className="mt-2 text-[12px] leading-snug text-text-muted whitespace-pre-wrap line-clamp-3 font-mono">
        {event.content}
      </pre>
    </div>
  );
}
