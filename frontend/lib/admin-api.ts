export interface DocumentListItem {
  doc_id: string;
  title: string;
  file_type: string | null;
  file_size: string | null;
  content_hash: string;
  chunks: number;
  created_at: string;
  source_path: string | null;
  stored: boolean;
}

const BASE = "/api/admin/documents";

async function handle(res: Response) {
  if (res.status === 204) return null;
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function listDocuments(): Promise<DocumentListItem[]> {
  const res = await fetch(BASE);
  return handle(res);
}

export async function renameDocument(docId: string, title: string): Promise<DocumentListItem> {
  const res = await fetch(`${BASE}/${docId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return handle(res);
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${BASE}/${docId}`, { method: "DELETE" });
  return handle(res);
}

export interface ReindexResponse {
  doc_id: string;
  title: string;
  chunks: number;
  took_ms: number;
}

export async function reindexDocument(docId: string): Promise<ReindexResponse> {
  const res = await fetch(`${BASE}/${docId}/reindex`, { method: "POST" });
  return handle(res);
}