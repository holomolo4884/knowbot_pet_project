"use client";
import { useEffect, useState } from "react";

type Phase = "searching" | "generating";

interface PhaseIndicatorProps {
  phase: Phase;
  hits?: number;
}

export function PhaseIndicator({ phase, hits }: PhaseIndicatorProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    setElapsed(0);
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, [phase]);

  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-blue-500" />
      {phase === "searching" ? (
        <span>Ищу в базе знаний…</span>
      ) : (
        <span>
          {hits != null && <span className="text-slate-400">Нашёл {hits} фрагментов · </span>}
          Формирую ответ… <span className="tabular-nums text-slate-400">{elapsed}с</span>
        </span>
      )}
    </div>
  );
}