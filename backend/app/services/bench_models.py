import asyncio
import time

from rich.console import Console
from rich.table import Table

from app.core.database import async_session_maker
from app.services.llm_service import llm_service
from app.services.prompt import STREAM_SYSTEM_PROMPT, build_user_prompt
from app.retrieval.retriever import Retriever

console = Console()

QUESTION = "Перечисли все требования к паролям и правила оформления отпуска подробно"

MODELS = [
    "gpt-5.6-sol",
    "claude-haiku-4-5",
    "gemini-3.8-flash",
    "qwen3.7-flash",
]


async def main() -> None:
    async with async_session_maker() as db:
        chunks, retrieval_ms = await Retriever(db).search(QUESTION, top_k=5)

    console.print(f"Контекст: {len(chunks)} чанков, retrieval {retrieval_ms} мс\n")
    user_prompt = build_user_prompt(QUESTION, chunks)
    original_model = llm_service.model

    table = Table(title="TTFT по моделям (один и тот же контекст)")
    table.add_column("Модель", style="cyan")
    table.add_column("TTFT, мс", justify="right")
    table.add_column("Total, мс", justify="right")
    table.add_column("Стрим, мс", justify="right")
    table.add_column("Символов", justify="right")

    for model in MODELS:
        llm_service.model = model
        started = time.perf_counter()
        ttft: float | None = None
        chars = 0

        try:
            async for piece in llm_service.stream_text(STREAM_SYSTEM_PROMPT, user_prompt):
                if ttft is None:
                    ttft = round((time.perf_counter() - started) * 1000, 1)
                chars += len(piece)
            total = round((time.perf_counter() - started) * 1000, 1)
            stream = round(total - (ttft or 0), 1)
            table.add_row(model, str(ttft), str(total), str(stream), str(chars))
        except Exception as e:
            table.add_row(model, "[red]error[/red]", str(e)[:40], "—", "—")

    llm_service.model = original_model
    console.print(table)
    console.print("\n[dim]Стрим = Total − TTFT. Чем меньше TTFT, тем лучше UX.[/dim]")


if __name__ == "__main__":
    asyncio.run(main())