"use client";

import { useEffect, useRef, useState } from "react";
import {
  indexRepository,
  listRepositories,
  streamQuery,
  type Repository,
  type RetrievalEvent,
} from "@/lib/api";
import { SourceCard } from "@/components/SourceCard";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type IndexState = "idle" | "indexing" | "done" | "error";
type QueryState = "idle" | "streaming" | "done" | "error";

function HealthDot() {
  const [up, setUp] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/health/`)
      .then((res) => setUp(res.ok))
      .catch(() => setUp(false));
  }, []);

  const color = up === null ? "bg-text-dim" : up ? "bg-teal" : "bg-red";
  const label = up === null ? "checking" : up ? "online" : "offline";
  return (
    <span className="flex items-center gap-2 text-xs text-text-muted">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}

export default function Home() {
  const [repoInput, setRepoInput] = useState("");
  const [branch, setBranch] = useState("main");
  const [indexState, setIndexState] = useState<IndexState>("idle");
  const [indexMessage, setIndexMessage] = useState("");
  const [repos, setRepos] = useState<Repository[]>([]);

  const [query, setQuery] = useState("");
  const [queryState, setQueryState] = useState<QueryState>("idle");
  const [sources, setSources] = useState<RetrievalEvent[]>([]);
  const [answer, setAnswer] = useState("");
  const [queryError, setQueryError] = useState("");
  const stopStream = useRef<(() => void) | null>(null);

  useEffect(() => {
    listRepositories().then(setRepos);
  }, [indexState]);

  async function onIndex(e: React.FormEvent) {
    e.preventDefault();
    const [owner, name] = repoInput.split("/").map((s) => s.trim());
    if (!owner || !name) {
      setIndexState("error");
      setIndexMessage("Give me owner/repo, like torvalds/linux.");
      return;
    }
    setIndexState("indexing");
    setIndexMessage(`Indexing ${owner}/${name}…`);
    try {
      await indexRepository(owner, name, branch || "main");
      setIndexState("done");
      setIndexMessage(`Queued ${owner}/${name} — indexing runs in the background, ask a question once it lands below.`);
    } catch (err) {
      setIndexState("error");
      setIndexMessage(err instanceof Error ? err.message : "Couldn't reach the indexer.");
    }
  }

  function onAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || queryState === "streaming") return;

    stopStream.current?.();
    setSources([]);
    setAnswer("");
    setQueryError("");
    setQueryState("streaming");

    stopStream.current = streamQuery(query, 5, {
      onEvent: (event) => {
        if (event.type === "retrieval") {
          setSources((prev) => [...prev, event]);
        } else if (event.type === "response") {
          setAnswer((prev) => prev + event.content);
        } else if (event.type === "error") {
          setQueryError(event.error);
        }
      },
      onDone: () => setQueryState("done"),
      onError: () => {
        setQueryState("error");
        setQueryError("The stream dropped — try asking again.");
      },
    });
  }

  return (
    <div className="flex-1 flex justify-center px-4 py-10 sm:py-16">
      <main className="w-full max-w-2xl flex flex-col gap-8">
        <header className="flex items-baseline justify-between border-b border-border pb-4">
          <div>
            <h1 className="text-xl tracking-tight text-text">VaulS<span className="text-amber">.ai</span></h1>
            <p className="text-xs text-text-muted mt-1">hybrid BM25 + vector retrieval over any public repo</p>
          </div>
          <HealthDot />
        </header>

        <section>
          <form onSubmit={onIndex} className="flex flex-col sm:flex-row gap-2">
            <div className="flex-1 flex items-center gap-2 border border-border bg-panel px-3 py-2">
              <span className="text-amber shrink-0">$ index</span>
              <input
                value={repoInput}
                onChange={(e) => setRepoInput(e.target.value)}
                placeholder="owner/repository"
                className="flex-1 bg-transparent outline-none text-text placeholder:text-text-dim min-w-0"
              />
            </div>
            <input
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="branch"
              className="w-full sm:w-28 border border-border bg-panel px-3 py-2 outline-none text-text placeholder:text-text-dim focus:border-border-bright"
            />
            <button
              type="submit"
              disabled={indexState === "indexing"}
              className="border border-border-bright bg-panel-raised px-4 py-2 text-amber hover:border-amber transition-colors disabled:opacity-50"
            >
              Index
            </button>
          </form>
          {indexMessage && (
            <p className={`mt-2 text-xs ${indexState === "error" ? "text-red" : "text-text-muted"}`}>
              {indexMessage}
            </p>
          )}
          {repos.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {repos.map((r) => (
                <span key={r.id} className="text-xs border border-border px-2 py-1 text-text-muted">
                  {r.owner}/{r.name}
                </span>
              ))}
            </div>
          )}
        </section>

        <section className="flex flex-col gap-4">
          <form onSubmit={onAsk} className="flex items-center gap-2 border border-border bg-panel px-3 py-2">
            <span className="text-teal shrink-0">&gt; ask</span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="a question about the indexed code"
              className="flex-1 bg-transparent outline-none text-text placeholder:text-text-dim min-w-0"
            />
            <button
              type="submit"
              disabled={queryState === "streaming"}
              className="text-teal hover:text-text transition-colors disabled:opacity-50 shrink-0"
            >
              {queryState === "streaming" ? "…" : "Ask"}
            </button>
          </form>

          {sources.length === 0 && queryState === "idle" && (
            <p className="text-sm text-text-dim">Index a repo, then ask it anything. Sources show up here as they're retrieved.</p>
          )}

          {sources.length > 0 && (
            <div className="flex flex-col gap-2">
              {sources.map((s, i) => (
                <SourceCard key={s.chunk_id} event={s} index={i} />
              ))}
            </div>
          )}

          {queryError && <p className="text-sm text-red">{queryError}</p>}

          {(answer || queryState === "streaming") && (
            <p className={`font-serif text-[15px] leading-relaxed text-text ${queryState === "streaming" ? "blink-cursor" : ""}`}>
              {answer}
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
