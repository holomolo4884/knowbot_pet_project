export interface Citation {
  index: number;
  chunk_id: string;
  doc_id: string;
  title: string | null;
  section_path: string | null;
  page_number: number | null;
  score: number;
}

export interface ChatResponse {
  question: string;
  answer: string;
  citations: Citation[];
  grounded: boolean;
  abstained: boolean;
  invalid_citation_markers: number;
  retrieval_ms: number;
  generation_ms: number;
  model: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  title: string | null;
  section_path: string | null;
  page_number: number | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  took_ms: number;
  results: RetrievedChunk[];
}

export interface HealthResponse {
  status: string;
  chunks_indexed: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  search: (query: string, topK = 5) =>
    request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    }),

  chat: (question: string, topK = 5) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ question, top_k: topK }),
    }),
};