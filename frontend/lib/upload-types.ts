export type UploadPhase =
  | "received"
  | "parsing"
  | "parsed"
  | "embedding"
  | "saving"
  | "duplicate";

export interface PhaseEvent {
  type: "phase";
  phase: UploadPhase;
  pct: number;
  size_mb?: number;
  hash?: string;
  chunks_found?: number;
  done?: number;
  total?: number;
}

export interface UploadDoneEvent {
  type: "done";
  doc_id?: string;
  title?: string;
  file_type?: string;
  chunks?: number;
  was_created?: boolean;
  took_ms?: number;
}

export interface UploadErrorEvent {
  type: "error";
  message: string;
}

export type UploadEvent = PhaseEvent | UploadDoneEvent | UploadErrorEvent;

export interface UploadResult {
  docId: string;
  title: string;
  fileType: string;
  chunks: number;
  wasCreated: boolean;
  tookMs: number;
}

export type UploadState =
  | { phase: "idle" }
  | {
      phase: "uploading";
      fileName: string;
      pct: number;
      label: string;
      detail: string | null;
    }
  | { phase: "done"; fileName: string; result: UploadResult }
  | { phase: "error"; fileName: string; message: string };

export const ALLOWED_EXT = [".md", ".markdown", ".docx", ".pdf"] as const;
export const MAX_SIZE_MB = 20;