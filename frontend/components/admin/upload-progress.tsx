"use client";

interface UploadProgressProps {
  fileName: string;
  pct: number;
  label: string;
  detail: string | null;
  onAbort: () => void;
}

export function UploadProgress({
  fileName,
  pct,
  label,
  detail,
  onAbort,
}: UploadProgressProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="truncate text-sm font-medium text-slate-800">
          {fileName}
        </span>
        <button
          type="button"
          onClick={onAbort}
          className="shrink-0 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
        >
          Отмена
        </button>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-blue-600 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between text-xs">
        <span className="text-slate-600">{label}</span>
        <span className="tabular-nums text-slate-400">
          {detail ? `${detail} · ` : ""}
          {pct}%
        </span>
      </div>
    </div>
  );
}