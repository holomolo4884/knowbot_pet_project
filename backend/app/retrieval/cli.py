import asyncio

import typer
from rich.console import Console
from rich.table import Table

from app.core.database import async_session_maker
from app.retrieval.retriever import Retriever

app = typer.Typer(help="CLI для поиска по базе знаний", no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """KnowBot Retrieval CLI."""


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Поисковый запрос"),
    top_k: int = typer.Option(5, "--top-k", help="Сколько чанков вернуть"),
    file_type: str = typer.Option(None, "--file-type", help="Фильтр: pdf / docx / md"),
) -> None:
    """Ищет релевантные чанки по векторному сходству."""

    async def _run():
        async with async_session_maker() as db:
            retriever = Retriever(db)
            return await retriever.search(query, top_k=top_k, file_type=file_type)

    results, took_ms = asyncio.run(_run())

    if not results:
        console.print("[yellow]Ничего не найдено. База пуста?[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Запрос: {query}  ({took_ms} ms)")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Score", style="green", justify="right")
    table.add_column("Раздел", style="cyan")
    table.add_column("Текст", style="white", max_width=60)

    for i, r in enumerate(results, 1):
        table.add_row(str(i), f"{r.score:.4f}", r.section_path or "—", r.text[:120])

    console.print(table)


if __name__ == "__main__":
    app()