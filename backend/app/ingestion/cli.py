import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .processor import IngestionProcessor

app = typer.Typer(help="CLI для парсинга документов", no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """
    KnowBot Ingestion CLI.

    Наличие callback заставляет Typer работать в режиме подкоманд,
    поэтому вызов выглядит как: python -m app.ingestion ingest <dir>
    """
    pass


@app.command("ingest")
def ingest(
    directory: Path = typer.Argument(..., help="Директория с документами (PDF, DOCX, MD)"),
    output: Path = typer.Option(
        "../data/parsed_output.json", help="Куда сохранить JSON результат"
    ),
) -> None:
    """Сканирует директорию, парсит документы и сохраняет в JSON."""
    processor = IngestionProcessor()

    console.print(f"[bold cyan]Обрабатываю директорию:[/bold cyan] {directory.absolute()}")

    try:
        documents = processor.process_directory(directory)
    except Exception as e:
        console.print(f"[red]Ошибка:[/red] {e}")
        raise typer.Exit(1)

    if not documents:
        console.print("[yellow]Подходящие документы не найдены.[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Результат парсинга")
    table.add_column("Файл", style="cyan")
    table.add_column("Тип", style="green")
    table.add_column("Чанков", style="magenta", justify="right")
    table.add_column("Doc ID", style="dim")

    for doc in documents:
        table.add_row(
            Path(doc.metadata.source_path).name,
            doc.metadata.file_type,
            str(len(doc.chunks)),
            doc.metadata.doc_id[:8] + "...",
        )

    console.print(table)

    processor.save_to_json(documents, output)
    console.print(f"[bold green]✓[/bold green] Сохранено в {output.absolute()}")


if __name__ == "__main__":
    app()