import type { StreamEvent } from "./chat-types";

interface ParserState {
  buffer: string;
}

export function createParser(): ParserState {
  return { buffer: "" };
}

/**
 * Скармливает парсеру новый кусок текста и возвращает завершённые события.
 * Незавершённое событие остаётся в буфере до следующего куска.
 */
export function feed<T = StreamEvent>(state: ParserState, chunk: string): T[] {
  state.buffer += chunk;
  const events: T[] = [];

  // SSE-события разделены двойным переводом строки
  while (true) {
    const boundary = state.buffer.indexOf("\n\n");
    if (boundary === -1) break;

    const frame = state.buffer.slice(0, boundary);
    state.buffer = state.buffer.slice(boundary + 2);

    const parsed = parseFrame<T>(frame);
    if (parsed) events.push(parsed);
  }

  return events;
}

function parseFrame<T>(frame: string): T | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
    // ignore: id, retry, comments (lines starting with ':')
  }

  if (dataLines.length === 0) return null;

  const payload = dataLines.join("\n");
  try {
    return { type: event, ...JSON.parse(payload) } as T;
  } catch {
    // Сломанный JSON — пропускаем, но логируем
    console.warn(`[sse-parser] bad JSON in event '${event}':`, payload);
    return null;
  }
}

/** Сброс буфера (например, при переподключении). */
export function reset(state: ParserState): void {
  state.buffer = "";
}