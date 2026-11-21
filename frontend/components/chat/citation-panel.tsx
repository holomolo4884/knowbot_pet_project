"use client";
import { useState } from "react";
import type { Citation } from "@/lib/chat-types";

interface CitationPanelProps {
  citations: Citation[];
  id?: string;
}

export function CitationPanel({ citations, id }: CitationPanelProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  if (citations.length === 0) return null;

  const toggle = (index: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div id={id} className="mt-3 border-t border-slate-200 pt-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-500">
        <span>Источники ({citations.length})</span>
      </div>
      <div className="space-y-1.5">
        {citations.map((c) => {
          const isOpen = expanded.has(c.index);
          return (
            <button
              key={c.index}
              type="button"
              onClick={() => toggle(c.index)}
              className="block w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs transition hover:border-slate-300"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex min-w-0 flex-1 items-start gap-2">
                  <span className="inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-sm bg-blue-600 px-1 font-semibold text-white">
                    {c.index}
                  </span>
                  <span className="truncate font-medium text-slate-700">
                    {c.section_path || c.title || "Без заголовка"}
                  </span>
                </div>
                <span className="shrink-0 tabular-nums text-slate-400">
                  {c.score.toFixed(2)}
                </span>
              </div>
              {isOpen && (
                <div className="mt-2 space-y-1 border-t border-slate-200 pt-2 text-slate-500">
                  {c.title && (
                    <div><span className="text-slate-400">Документ:</span> {c.title}</div>
                  )}
                  {c.page_number && (
                    <div><span className="text-slate-400">Страница:</span> {c.page_number}</div>
                  )}
                  <div className="truncate font-mono">
                    <span className="text-slate-400">ID:</span> {c.chunk_id.slice(0, 8)}
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}