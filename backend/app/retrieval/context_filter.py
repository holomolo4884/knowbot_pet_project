from app.retrieval.schemas import RetrievedChunk


def select_context(
    chunks: list[RetrievedChunk],
    max_gap: float = 0.035,
    min_keep: int = 1,
    max_keep: int = 5,
) -> list[RetrievedChunk]:
    """Отбирает чанки для контекста по разрыву в score, а не по абсолютному порогу.

    Ищем первый значимый разрыв между соседями в отсортированном списке.
    Если разрыва нет (плотный кластер) — оставляем весь пул: лучше дать
    LLM больше контекста, чем выкинуть релевантный чанк из-за сжатого диапазона.
    """
    if not chunks:
        return []

    pool = chunks[:max_keep]
    for i in range(len(pool) - 1):
        gap = pool[i].score - pool[i + 1].score
        if gap >= max_gap and i + 1 >= min_keep:
            return pool[: i + 1]
    return pool