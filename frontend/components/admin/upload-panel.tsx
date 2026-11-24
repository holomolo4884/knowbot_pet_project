"use client";

import Link from "next/link";
import { useUpload } from "@/hooks/use-upload";
import { Dropzone } from "./dropzone";
import { UploadProgress } from "./upload-progress";

export function UploadPanel() {
  const { state, history, upload, abort, reset } = useUpload();
  const busy = state.phase === "uploading";

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Загрузка документов</h1>
          <p className="text-sm text-slate-500">
            Файл парсится, чанкуется и индексируется. Повторная загрузка того же
            файла не создаёт дубликат.
          </p>
        </div>
        <Link
          href="/"
          className="shrink-0 rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          ← К чату
        </Link>
      </header>

      <Dropzone onFile={upload} disabled={busy} />

      {state.phase === "uploading" && (
        <UploadProgress
          fileName={state.fileName}
          pct={state.pct}
          label={state.label}
          detail={state.detail}
          onAbort={abort}
        />
      )}

      {state.phase === "done" && (
        <div
          className={`rounded-xl border p-4 ${
            state.result.wasCreated
              ? "border-green-200 bg-green-50"
              : "border-blue-200 bg-blue-50"
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-medium text-slate-900">
                {state.result.wasCreated
                  ? "✓ Документ проиндексирован"
                  : "ℹ Документ уже был в базе"}
              </div>
              <div className="mt-1 text-sm text-slate-700">
                {state.result.title} · {state.result.fileType} ·{" "}
                {state.result.chunks} чанков · {state.result.tookMs.toFixed(0)} мс
              </div>
            </div>
            <button
              type="button"
              onClick={reset}
              className="shrink-0 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
            >
              Ещё файл
            </button>
          </div>
        </div>
      )}

      {state.phase === "error" && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <div className="font-medium text-red-900">Ошибка загрузки</div>
          <div className="mt-1 text-sm text-red-700">{state.message}</div>
          <button
            type="button"
            onClick={reset}
            className="mt-3 rounded-md border border-red-300 bg-white px-2 py-1 text-xs text-red-700 hover:bg-red-50"
          >
            Попробовать снова
          </button>
        </div>
      )}

      {history.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-medium text-slate-500">
            Загружено в этой сессии ({history.length})
          </h2>
          <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
            {history.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium text-slate-800">
                    {h.title}
                  </div>
                  <div className="text-xs text-slate-400">
                    {h.fileName} · {h.at}
                  </div>
                </div>
                <div className="shrink-0 text-right text-xs">
                  <div className="text-slate-600">{h.chunks} чанков</div>
                  <div
                    className={
                      h.wasCreated ? "text-green-600" : "text-blue-600"
                    }
                  >
                    {h.wasCreated ? "новый" : "дубликат"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}