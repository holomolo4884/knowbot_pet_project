import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from app.core.database import async_session_maker
from app.retrieval.retriever import Retriever

console = Console()
DATASET = Path(__file__).resolve().parents[3] / "eval" / "datasets" / "smoke.jsonl"


async def main() -> None:
    cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]

    table = Table(title="Smoke eval: hit@1 / hit@3")
    table.add_column("Вопрос", max_width=45)
    table.add_column("hit@1", justify="center")
    table.add_column("hit@3", justify="center")
    table.add_column("Топ-1 раздел", max_width=35)

    hit1 = hit3 = 0
    async with async_session_maker() as db:
        retriever = Retriever(db)
        for case in cases:
            results, _ = await retriever.search(case["question"], top_k=3)
            sections = [r.section_path or "" for r in results]
            expected = case["expected_section"]

            at1 = bool(sections) and expected in sections[0]
            at3 = any(expected in s for s in sections)
            hit1 += at1
            hit3 += at3

            table.add_row(
                case["question"],
                "[green]✓[/green]" if at1 else "[red]✗[/red]",
                "[green]✓[/green]" if at3 else "[red]✗[/red]",
                sections[0] if sections else "—",
            )

    console.print(table)
    n = len(cases)
    console.print(f"\n[bold]hit@1 = {hit1}/{n} ({hit1/n:.0%})   hit@3 = {hit3}/{n} ({hit3/n:.0%})[/bold]")


if __name__ == "__main__":
    asyncio.run(main())