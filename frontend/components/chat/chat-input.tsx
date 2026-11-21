"use client";
import { useEffect, useRef, useState } from "react";

interface ChatInputProps {
  onSubmit: (text: string) => void;
  onAbort: () => void;
  disabled?: boolean;
  isGenerating?: boolean;
}

export function ChatInput({
  onSubmit,
  onAbort,
  disabled,
  isGenerating,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Автоувеличение высоты textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === "Escape" && isGenerating) {
      onAbort();
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isGenerating
              ? "Генерирую ответ… (Esc для отмены)"
              : "Задайте вопрос по базе знаний…"
          }
          rows={1}
          className="flex-1 resize-none rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          disabled={disabled && !isGenerating}
        />
        {isGenerating ? (
          <button
            type="button"
            onClick={onAbort}
            className="shrink-0 rounded-lg bg-slate-700 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Отмена
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!value.trim() || disabled}
            className="shrink-0 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Отправить
          </button>
        )}
      </div>
      <div className="mx-auto mt-2 max-w-3xl text-[11px] text-slate-400">
        Enter — отправить · Shift+Enter — новая строка · Esc — отменить
      </div>
    </div>
  );
}