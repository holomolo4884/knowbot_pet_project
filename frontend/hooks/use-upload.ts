"use client";

import { useCallback, useRef, useState } from "react";
import { openUploadStream } from "@/lib/upload-api";
import {
  ALLOWED_EXT,
  MAX_SIZE_MB,
  type PhaseEvent,
  type UploadResult,
  type UploadState,
} from "@/lib/upload-types";

export interface HistoryItem extends UploadResult {
  id: string;
  fileName: string;
  at: string;
}

function describe(ev: PhaseEvent): { label: string; detail: string | null } {
  switch (ev.phase) {
    case "received":
      return {
        label: "Файл получен",
        detail: `${ev.size_mb?.toFixed(2)} МБ · hash ${ev.hash}`,
      };
    case "parsing":
      return { label: "Извлекаю текст и структуру…", detail: null };
    case "parsed":
      return { label: "Документ разобран", detail: `${ev.chunks_found} чанков` };
    case "embedding":
      return {
        label: "Считаю эмбеддинги…",
        detail: `${ev.done} / ${ev.total}`,
      };
    case "saving":
      return { label: "Сохраняю в базу…", detail: null };
    case "duplicate":
      return { label: "Файл уже в базе", detail: "переиндексация не нужна" };
  }
}

export function useUpload() {
  const [state, setState] = useState<UploadState>({ phase: "idle" });
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const controllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setState({ phase: "idle" });
  }, []);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setState({ phase: "idle" });
  }, []);

  const upload = useCallback((file: File) => {
    controllerRef.current?.abort();

    const lower = file.name.toLowerCase();
    if (!ALLOWED_EXT.some((ext) => lower.endsWith(ext))) {
      setState({
        phase: "error",
        fileName: file.name,
        message: `Неподдерживаемый формат. Доступны: ${ALLOWED_EXT.join(", ")}`,
      });
      return;
    }

    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > MAX_SIZE_MB) {
      setState({
        phase: "error",
        fileName: file.name,
        message: `Файл слишком большой: ${sizeMb.toFixed(1)} МБ > ${MAX_SIZE_MB} МБ`,
      });
      return;
    }

    setState({
      phase: "uploading",
      fileName: file.name,
      pct: 0,
      label: "Отправляю файл…",
      detail: null,
    });

    controllerRef.current = openUploadStream(file, {
      onEvent: (ev) => {
        if (ev.type === "phase") {
          const { label, detail } = describe(ev);
          setState({
            phase: "uploading",
            fileName: file.name,
            pct: ev.pct,
            label,
            detail,
          });
          return;
        }

        if (ev.type === "error") {
          setState({ phase: "error", fileName: file.name, message: ev.message });
          controllerRef.current = null;
          return;
        }

        if (ev.type === "done" && ev.doc_id) {
          const result: UploadResult = {
            docId: ev.doc_id,
            title: ev.title ?? file.name,
            fileType: ev.file_type ?? "",
            chunks: ev.chunks ?? 0,
            wasCreated: ev.was_created ?? false,
            tookMs: ev.took_ms ?? 0,
          };
          setState({ phase: "done", fileName: file.name, result });
          setHistory((prev) => [
            {
              ...result,
              id: crypto.randomUUID(),
              fileName: file.name,
              at: new Date().toLocaleTimeString("ru-RU"),
            },
            ...prev,
          ]);
          controllerRef.current = null;
        }
      },
      onError: (err) => {
        setState({ phase: "error", fileName: file.name, message: err.message });
        controllerRef.current = null;
      },
    });
  }, []);

  return { state, history, upload, abort, reset };
}