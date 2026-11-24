import { createParser, feed } from "./sse-parser";
import type { UploadEvent } from "./upload-types";

export interface UploadCallbacks {
  onEvent: (event: UploadEvent) => void;
  onError: (error: Error) => void;
}

export function openUploadStream(
  file: File,
  callbacks: UploadCallbacks,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const form = new FormData();
      form.append("file", file);

      // Content-Type НЕ указываем: браузер сам поставит boundary
      const res = await fetch("/api/admin/documents/upload/stream", {
        method: "POST",
        body: form,
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      }
      if (!res.body) {
        throw new Error("Сервер вернул пустой ответ");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      const parser = createParser();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const ev of feed<UploadEvent>(parser, text)) {
          callbacks.onEvent(ev);
        }
      }

      for (const ev of feed<UploadEvent>(parser, "\n\n")) {
        callbacks.onEvent(ev);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}