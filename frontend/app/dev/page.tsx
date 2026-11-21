"use client";

import { useChatStream } from "@/hooks/use-chat-stream";

export default function DevChat() {
  const { state, ask, abort, reset } = useChatStream();

  return (
    <main className="mx-auto max-w-3xl p-8 space-y-4 font-mono text-sm">
      <h1 className="text-xl font-bold">SSE Stream Dev Console</h1>

      <div className="flex gap-2">
        <button
          className="px-3 py-1.5 bg-blue-600 text-white rounded"
          onClick={() =>
            ask("Какой минимальной длины должен быть пароль?", 3)
          }
        >
          Вопрос 1 (пароль)
        </button>
        <button
          className="px-3 py-1.5 bg-blue-600 text-white rounded"
          onClick={() => ask("Какая погода на Марсе?")}
        >
          Вопрос 2 (off-topic)
        </button>
        <button
          className="px-3 py-1.5 bg-blue-600 text-white rounded"
          onClick={() =>
            ask(
              "Перечисли все требования к паролям и правила оформления отпуска подробно",
              5,
            )
          }
        >
          Вопрос 3 (multi-hop)
        </button>
        <button
          className="px-3 py-1.5 bg-yellow-600 text-white rounded"
          onClick={abort}
        >
          Abort
        </button>
        <button
          className="px-3 py-1.5 bg-gray-600 text-white rounded"
          onClick={reset}
        >
          Reset
        </button>
      </div>

      <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-[70vh]">
        {JSON.stringify(state, null, 2)}
      </pre>
    </main>
  );
}