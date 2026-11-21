import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.database import async_session_maker
from app.services.rag_schemas import ChatRequest
from app.services.rag_service import RAGService

app = typer.Typer(help="Задать вопрос базе знаний", no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """KnowBot Ask CLI."""


@app.command("ask")
def ask(
    question: str = typer.Argument(..., help="Вопрос"),
    top_k: int = typer.Option(5, "--top-k"),
) -> None:
    async def _run():
        async with async_session_maker() as db:
            return await RAGService(db).answer(ChatRequest(question=question, top_k=top_k))

    res = asyncio.run(_run())

    color = "yellow" if res.abstained else ("green" if res.grounded else "red")
    console.print(Panel(res.answer, title=f"Ответ [{color}]", border_style=color))

    if res.citations:
        table = Table(title="Источники")
        table.add_column("[N]", justify="right")
        table.add_column("Документ")
        table.add_column("Раздел", max_width=45)
        table.add_column("Score", justify="right")
        for c in res.citations:
            table.add_row(str(c.index), c.title or "—", c.section_path or "—", f"{c.score:.4f}")
        console.print(table)

    console.print(
        f"[dim]grounded={res.grounded} abstained={res.abstained} "
        f"invalid_markers={res.invalid_citation_markers} "
        f"retrieval={res.retrieval_ms}ms generation={res.generation_ms}ms "
        f"model={res.model}[/dim]"
    )


if __name__ == "__main__":
    app()