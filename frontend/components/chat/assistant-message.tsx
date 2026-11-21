"use client";
import type { ChatState } from "@/lib/chat-types";
import { CitationPanel } from "./citation-panel";
import { Markdown } from "./markdown";
import { PhaseIndicator } from "./phase-indicator";

interface AssistantMessageProps {
  state: ChatState;
}

export function AssistantMessage({ state }: AssistantMessageProps) {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-purple-600 text-sm font-semibold text-white">
        KB
      </div>
      <div className="min-w-0 flex-1">
        {state.phase === "idle" && null}

        {state.phase === "searching" && (
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <PhaseIndicator phase="searching" />
          </div>
        )}

        {state.phase === "generating" && (
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <PhaseIndicator phase="generating" hits={state.hits} />
            {state.text && (
              <div className="mt-3 text-slate-800">
                <Markdown text={state.text} />
              </div>
            )}
          </div>
        )}

        {state.phase === "done" && <DoneMessage state={state} />}

        {state.phase === "error" && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
            <div className="mb-1 font-medium">Ошибка</div>
            <div className="text-sm">{state.message}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function DoneMessage({
  state,
}: {
  state: Extract<ChatState, { phase: "done" }>;
}) {
  if (state.abstained) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
        <div className="flex items-start gap-2">
          <span className="text-lg">🤔</span>
          <div>
            <div className="font-medium text-amber-900">В базе знаний нет информации по этому вопросу</div>
            <div className="mt-1 text-sm text-amber-700">
              Я не могу отвечать вне базы знаний. Попробуйте переформулировать вопрос или уточнить, что именно вас интересует.
            </div>
          </div>
        </div>
        <Timings state={state} />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="text-slate-800">
        <Markdown
          text={state.text}
          onCitationClick={(index) => {
            document.getElementById(`citation-${index}`)?.scrollIntoView({
              behavior: "smooth",
              block: "center",
            });
          }}
        />
      </div>
      <CitationPanel citations={state.citations} />
      {state.invalid_citation_markers > 0 && (
        <div className="mt-2 rounded border border-yellow-200 bg-yellow-50 px-2 py-1 text-xs text-yellow-800">
          ⚠ Удалено галлюцинированных ссылок: {state.invalid_citation_markers}
        </div>
      )}
      <Timings state={state} />
    </div>
  );
}

function Timings({
  state,
}: {
  state: Extract<ChatState, { phase: "done" }>;
}) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-100 pt-2 text-[11px] text-slate-400">
      <span>Retrieval: <b className="tabular-nums text-slate-600">{state.retrieval_ms.toFixed(0)}мс</b></span>
      {state.ttft_ms != null && (
        <span>TTFT: <b className="tabular-nums text-slate-600">{state.ttft_ms.toFixed(0)}мс</b></span>
      )}
      <span>Generation: <b className="tabular-nums text-slate-600">{state.generation_ms.toFixed(0)}мс</b></span>
      <span className="font-mono">{state.model}</span>
      <span
        className={`rounded px-1.5 py-0.5 ${
          state.grounded ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
        }`}
      >
        {state.grounded ? "grounded" : "ungrounded"}
      </span>
    </div>
  );
}