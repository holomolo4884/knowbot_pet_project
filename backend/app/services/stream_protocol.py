import json


def sse(event: str, data: dict) -> str:
    """Формирует один SSE-фрейм."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class CitationStreamFilter:
    """Фильтрует маркеры [N] на лету, не разрывая поток.

    Буферизует потенциальный маркер до закрывающей ']',
    затем решает: пропустить (валидный) или вырезать (галлюцинация).
    Работает корректно, даже если маркер разорван между чанками.
    """

    MAX_PENDING = 8  # '[999]' + запас

    def __init__(self, total_chunks: int) -> None:
        self.total = total_chunks
        self.pending = ""
        self.valid: dict[int, None] = {}
        self.invalid_count = 0

    def feed(self, chunk: str) -> str:
        self.pending += chunk
        out: list[str] = []

        while True:
            start = self.pending.find("[")
            if start == -1:
                out.append(self.pending)
                self.pending = ""
                break

            out.append(self.pending[:start])
            self.pending = self.pending[start:]

            end = self.pending.find("]")
            if end == -1:
                # Маркер ещё не закрыт — ждём следующий чанк,
                # но не бесконечно (может быть просто '[' в тексте)
                if len(self.pending) > self.MAX_PENDING:
                    out.append(self.pending)
                    self.pending = ""
                break

            inner = self.pending[1:end]
            token = self.pending[: end + 1]
            self.pending = self.pending[end + 1 :]

            if inner.isdigit():
                n = int(inner)
                if 1 <= n <= self.total:
                    self.valid.setdefault(n, None)
                    out.append(token)
                else:
                    self.invalid_count += 1  # галлюцинация — вырезаем
            else:
                out.append(token)  # обычные скобки, не цитата

        return "".join(out)

    def flush(self) -> str:
        rest, self.pending = self.pending, ""
        return rest

    @property
    def indices(self) -> list[int]:
        return list(self.valid)