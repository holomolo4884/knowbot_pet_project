"use client";

import { useEffect, useRef, useState } from "react";
import { useChatStream } from "@/hooks/use-chat-stream";
import type { ChatState, Message } from "@/lib/chat-types";
import { AssistantMessage } from "./assistant-message";
import { ChatInput } from "./chat-input";
import { UserMessage } from "./user-message";

export function ChatContainer() {
  const { state, ask, abort, reset } = useChatStream();
  const [messages, setMessages] = useState<Message[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // При переходе в done — сохраняем сообщение в историю
  useEffect(() => {
    if (state.phase !== "done") return;
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === "assistant" && last.state?.phase === "generating") {
        // Заменяем "generating"-заглушку на финальное сообщение
        return [
          ...prev.slice(0, -1),
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: state.text,
            citations: state.citations,
            meta: {
              grounded: state.grounded,
              abstained: state.abstained,
              invalid_citation_markers: state.invalid_citation_markers,
              retrieval_ms: state.retrieval_ms,
              ttft_ms: state.ttft_ms,
              generation_ms: state.generation_ms,
              model: state.model,
            },
            state,
          },
        ];
      }
      return [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: state.text,
          citations: state.citations,
          meta: {
            grounded: state.grounded,
            abstained: state.abstained,
            invalid_citation_markers: state.invalid_citation_markers,
            retrieval_ms: state.retrieval_ms,
            ttft_ms: state.ttft_ms,
            generation_ms: state.generation_ms,
            model: state.model,
          },
          state,
        },
      ];
    });
  }, [state]);

  // Auto-scroll при новых сообщениях или delta
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, state]);

  const handleSubmit = (text: string) => {
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: text },
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        state: { phase: "searching" } as ChatState,
      },
    ]);
    ask(text);
  };

  const handleNewChat = () => {
    reset();
    setMessages([]);
  };

  const isGenerating =
    state.phase === "searching" || state.phase === "generating";

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      {/* Шапка */}
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">KnowBot</h1>
          <p className="text-xs text-slate-500">
            AI-ассистент по внутренней базе знаний
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/admin/upload"
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
          >
            Документы
          </a>
          <button
            type="button"
            onClick={handleNewChat}
            className="rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
          >
            Новый чат
          </button>
        </div>
      </header>

      {/* Лента сообщений */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 px-6 py-6">
          {messages.length === 0 ? (
            <EmptyState onSuggest={handleSubmit} />
          ) : (
            messages.map((m, idx) => {
              if (m.role === "user") {
                return <UserMessage key={m.id} text={m.content} />;
              }
              // Для assistant берём state из актуального state-хука,
              // если это последнее сообщение и оно ещё генерируется
              const isLast = idx === messages.length - 1;
              const displayState: ChatState =
                isLast && isGenerating ? state : (m.state ?? { phase: "idle" });
              return <AssistantMessage key={m.id} state={displayState} />;
            })
          )}
        </div>
      </div>

      {/* Инпут */}
      <ChatInput
        onSubmit={handleSubmit}
        onAbort={abort}
        isGenerating={isGenerating}
      />
    </div>
  );
}

function EmptyState({ onSuggest }: { onSuggest: (q: string) => void }) {
  const suggestions = [
    "Какой минимальной длины должен быть пароль?",
    "За сколько дней подавать заявление на отпуск?",
    "Перечисли все требования к паролям и правила оформления отпуска",
  ];

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 text-2xl font-bold text-white shadow-lg">
        KB
      </div>
      <h2 className="mb-2 text-2xl font-semibold text-slate-900">
        Чем могу помочь?
      </h2>
      <p className="mb-8 max-w-md text-slate-500">
        Спросите что-нибудь из внутренних документов компании.
        Отвечу со ссылками на источники.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onSuggest(s)}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}