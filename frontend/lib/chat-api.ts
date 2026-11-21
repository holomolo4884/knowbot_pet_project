import { createParser, feed } from "./sse-parser";
import type { StreamEvent } from "./chat-types";

export interface ChatStreamRequest {
  question: string;
  top_k?: number;
  doc_id?: string;
  file_type?: string;
}

export interface ChatStreamCallbacks {
  onEvent: (event: StreamEvent) => void;
  onError: (error: Error) => void;
}

/**
 * Открывает SSE-стрим к /chat/stream.
 * Возвращает AbortController — его .abort() остановит стрим.
 */
export function openChatStream(
  req: ChatStreamRequest,
  callbacks: ChatStreamCallbacks,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: req.question,
          top_k: req.top_k ?? 5,
          doc_id: req.doc_id,
          file_type: req.file_type,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      }
      if (!res.body) {
        throw new Error("Response body is null");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      const parser = createParser();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const events = feed(parser, text);
        for (const ev of events) {
          callbacks.onEvent(ev);
        }
      }

      // Flush-хвост буфера (последнее событие могло не иметь '\n\n' в конце)
      const trailing = feed(parser, "\n\n");
      for (const ev of trailing) {
        callbacks.onEvent(ev);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // Пользователь отменил — не ошибка
        return;
      }
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}