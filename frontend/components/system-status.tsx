"use client";

import { useEffect, useState } from "react";
import { api, type HealthResponse } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function SystemStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(String(e)));
  }, []);

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm font-medium">Состояние API</span>
        {error ? (
          <Badge variant="destructive">Недоступен</Badge>
        ) : health ? (
          <Badge variant="secondary">Подключён · {health.chunks_indexed} чанков</Badge>
        ) : (
          <Badge variant="outline">Проверка…</Badge>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-red-600 break-all">{error}</p>}
    </Card>
  );
}