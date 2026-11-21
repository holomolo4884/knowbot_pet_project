import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";

interface MarkdownProps {
  text: string;
  onCitationClick?: (index: number) => void;
}

/**
 * Рендерит markdown, заменяя [N] на кликабельные бейджи цитат.
 * Работает на уровне React, не на уровне текста —
 * поэтому markdown-синтаксис сохраняется.
 */
export function Markdown({ text, onCitationClick }: MarkdownProps) {
  const CitationBadge: Components["sup"] = ({ children, ...rest }) => {
    const content = String(children);
    const match = content.match(/^\[(\d+)\]$/);
    if (match) {
      const n = parseInt(match[1], 10);
      return (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            onCitationClick?.(n);
          }}
          className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-sm bg-blue-100 px-1 text-xs font-semibold text-blue-700 hover:bg-blue-200"
          title={`Источник [${n}]`}
        >
          {n}
        </button>
      );
    }
    return <sup {...rest}>{children}</sup>;
  };

  return (
    <ReactMarkdown
      components={{
        sup: CitationBadge,
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-2 list-disc pl-5">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 list-decimal pl-5">{children}</ol>,
        code: ({ children, className }) => {
          const isBlock = className?.includes("language-");
          if (isBlock) {
            return (
              <pre className="my-2 overflow-x-auto rounded-md bg-slate-800 p-3 text-sm text-slate-100">
                <code className={className}>{children}</code>
              </pre>
            );
          }
          return (
            <code className="rounded bg-slate-100 px-1 py-0.5 text-[0.9em] text-slate-800">
              {children}
            </code>
          );
        },
      }}
    >
      {text}
    </ReactMarkdown>
  );
}