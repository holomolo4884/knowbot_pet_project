// === События стрима ===

export interface RetrievalEvent {
  type: "retrieval";
  hits: number;
  context_hits?: number;
  best_score: number;
  took_ms: number;
}

export interface DeltaEvent {
  type: "delta";
  text: string;
}

export interface Citation {
  index: number;
  chunk_id: string;
  doc_id: string;
  title: string | null;
  section_path: string | null;
  page_number: number | null;
  score: number;
}

export interface CitationsEvent {
  type: "citations";
  items: Citation[];
}

export interface MetaEvent {
  type: "meta";
  grounded: boolean;
  abstained: boolean;
  invalid_citation_markers: number;
  retrieval_ms: number;
  ttft_ms: number | null;
  generation_ms: number;
  model: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export interface DoneEvent {
  type: "done";
}

export type StreamEvent =
  | RetrievalEvent
  | DeltaEvent
  | CitationsEvent
  | MetaEvent
  | ErrorEvent
  | DoneEvent;

// === Состояние чата (для UI) ===

export type ChatState =
  | { phase: "idle" }
  | { phase: "searching" }
  | {
      phase: "generating";
      hits: number;
      best_score: number;
      retrieval_ms: number;
      text: string;
    }
  | {
      phase: "done";
      text: string;
      citations: Citation[];
      grounded: boolean;
      abstained: boolean;
      invalid_citation_markers: number;
      retrieval_ms: number;
      generation_ms: number;
      ttft_ms: number | null;
      model: string;
    }
  | { phase: "error"; message: string };

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  meta?: Omit<MetaEvent, "type">;
  state?: ChatState;
}