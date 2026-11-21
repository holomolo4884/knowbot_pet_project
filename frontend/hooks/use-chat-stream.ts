import { useCallback, useRef, useState } from "react";
import { openChatStream } from "@/lib/chat-api";
import type { ChatState, Citation, MetaEvent } from "@/lib/chat-types";

interface UseChatStream {
  state: ChatState;
  ask: (question: string, topK?: number) => void;
  abort: () => void;
  reset: () => void;
}

export function useChatStream(): UseChatStream {
  const [state, setState] = useState<ChatState>({ phase: "idle" });
  const controllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
  }, []);

  const reset = useCallback(() => {
    abort();
    setState({ phase: "idle" });
  }, [abort]);

  const ask = useCallback((question: string, topK = 5) => {
    abort();
    setState({ phase: "searching" });

    const acc: {
      text: string;
      citations: Citation[];
      meta: MetaEvent | null;
      retrieval: null | { hits: number; best_score: number; took_ms: number };
    } = {
      text: "",
      citations: [],
      meta: null,
      retrieval: null,
    };

    controllerRef.current = openChatStream(
      { question, top_k: topK },
      {
        onEvent: (ev) => {
          switch (ev.type) {
            case "retrieval":
              acc.retrieval = {
                hits: ev.hits,
                best_score: ev.best_score,
                took_ms: ev.took_ms,
              };
              setState({
                phase: "generating",
                hits: ev.hits,
                best_score: ev.best_score,
                retrieval_ms: ev.took_ms,
                text: "",
              });
              break;

            case "delta":
              acc.text += ev.text;
              if (acc.retrieval) {
                setState({
                  phase: "generating",
                  hits: acc.retrieval.hits,
                  best_score: acc.retrieval.best_score,
                  retrieval_ms: acc.retrieval.took_ms,
                  text: acc.text,
                });
              }
              break;

            case "citations":
              acc.citations = ev.items;
              break;

            case "meta":
              acc.meta = ev;
              break;

            case "done":
              setState({
                phase: "done",
                text: acc.text,
                citations: acc.citations,
                grounded: acc.meta?.grounded ?? false,
                abstained: acc.meta?.abstained ?? false,
                invalid_citation_markers: acc.meta?.invalid_citation_markers ?? 0,
                retrieval_ms: acc.meta?.retrieval_ms ?? 0,
                generation_ms: acc.meta?.generation_ms ?? 0,
                ttft_ms: acc.meta?.ttft_ms ?? null,
                model: acc.meta?.model ?? "unknown",
              });
              controllerRef.current = null;
              break;

            case "error":
              setState({ phase: "error", message: ev.message });
              controllerRef.current = null;
              break;
          }
        },
        onError: (err) => {
          setState({ phase: "error", message: err.message });
          controllerRef.current = null;
        },
      },
    );
  }, [abort]);

  return { state, ask, abort, reset };
}