const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Repository = {
  id: string;
  owner: string;
  name: string;
  url: string;
  branch: string;
  last_indexed: string | null;
};

export type RetrievalEvent = {
  type: "retrieval";
  rank: number;
  chunk_id: string;
  file_path: string;
  content: string;
  scores: { bm25: number; vector: number; hybrid: number; rerank: number };
};

export type ResponseEvent = { type: "response"; content: string };

export type CompleteEvent = {
  type: "complete";
  query: string;
  retrieval_time_ms: number;
  sources_count: number;
};

export type ErrorEvent = { type: "error"; error: string };

export type StreamEvent = RetrievalEvent | ResponseEvent | CompleteEvent | ErrorEvent;

export async function indexRepository(owner: string, name: string, branch: string) {
  const res = await fetch(`${API_URL}/api/repositories/index/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ owner, name, branch }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Indexing failed (${res.status})`);
  }
  return res.json();
}

export async function listRepositories(): Promise<Repository[]> {
  const res = await fetch(`${API_URL}/api/repositories/`);
  if (!res.ok) return [];
  const body = await res.json();
  return body.results ?? body;
}

export function streamQuery(
  query: string,
  topK: number,
  handlers: {
    onEvent: (event: StreamEvent) => void;
    onDone: () => void;
    onError: () => void;
  }
): () => void {
  const url = `${API_URL}/api/query/stream/?q=${encodeURIComponent(query)}&top_k=${topK}`;
  const source = new EventSource(url);

  source.onmessage = (msg) => {
    const event = JSON.parse(msg.data) as StreamEvent;
    handlers.onEvent(event);
    if (event.type === "complete" || event.type === "error") {
      source.close();
      handlers.onDone();
    }
  };

  source.onerror = () => {
    source.close();
    handlers.onError();
  };

  return () => source.close();
}
