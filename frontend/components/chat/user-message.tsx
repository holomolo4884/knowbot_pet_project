interface UserMessageProps {
  text: string;
}

export function UserMessage({ text }: UserMessageProps) {
  return (
    <div className="flex gap-3 justify-end">
      <div className="max-w-[80%] rounded-lg bg-blue-600 px-4 py-3 text-white shadow-sm">
        <div className="whitespace-pre-wrap break-words">{text}</div>
      </div>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-sm font-semibold text-slate-700">
        Я
      </div>
    </div>
  );
}