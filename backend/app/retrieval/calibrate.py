import asyncio

from rich.console import Console
from rich.table import Table

from app.core.config import settings
from app.core.database import async_session_maker
from app.retrieval.retriever import Retriever

console = Console()

ON_TOPIC = [
    "Какой минимальной длины должен быть пароль?",
    "Можно ли передавать пароль коллегам?",
    "За сколько дней подавать заявление на отпуск?",
    "Во сколько начинается рабочий день?",
    "Сколько часов длится стандартный рабочий день?",
    "Какие символы обязательно должны быть в пароле?",
]

OFF_TOPIC = [
    "Какая погода на поверхности Марса?",
    "Кто выиграл чемпионат мира по футболу?",
    "Как приготовить борщ?",
    "Сколько стоит биткоин?",
    "Кто написал Войну и мир?",
    "Как настроить Kubernetes кластер?",
]


async def main() -> None:
    table = Table(title="Калибровка порога релевантности")
    table.add_column("Тип", style="cyan")
    table.add_column("Вопрос", max_width=45)
    table.add_column("best_score", justify="right")

    pos: list[float] = []
    neg: list[float] = []

    async with async_session_maker() as db:
        retriever = Retriever(db)
        for label, questions, bucket in (
            ("on-topic", ON_TOPIC, pos),
            ("off-topic", OFF_TOPIC, neg),
        ):
            for q in questions:
                chunks, _ = await retriever.search(q, top_k=3)
                score = max((c.score for c in chunks), default=0.0)
                bucket.append(score)
                color = "green" if label == "on-topic" else "yellow"
                table.add_row(label, q, f"[{color}]{score:.4f}[/{color}]")

    console.print(table)

    min_pos, max_neg = min(pos), max(neg)
    recommended = round((min_pos + max_neg) / 2, 3)

    console.print(f"\non-topic  min = {min_pos:.4f}")
    console.print(f"off-topic max = {max_neg:.4f}")
    console.print(f"текущий порог = {settings.MIN_RELEVANCE_SCORE}")

    if max_neg >= min_pos:
        console.print("[red]Распределения пересекаются — порог не разделит классы.[/red]")
        console.print("[red]Нужен reranker или hybrid search (Этап 10).[/red]")
    else:
        console.print(f"[bold green]Рекомендуемый порог = {recommended}[/bold green]")
        console.print(f"зазор: {min_pos - recommended:.4f} сверху, {recommended - max_neg:.4f} снизу")


if __name__ == "__main__":
    asyncio.run(main())