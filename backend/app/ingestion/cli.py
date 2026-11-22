import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from loguru import logger

from .processor import IngestionProcessor
from app.core.database import async_session_maker
from app.services.embedding_service import embedding_service
from app.services.content_hash import compute_content_hash
from app.repositories.document_repository import DocumentRepository

app = typer.Typer(help="CLI для парсинга документов", no_args_is_help=True)
console = Console()

@app.callback()
def main() -> None:
    pass

@app.command("ingest")
def ingest(
    directory: Path = typer.Argument(..., help="Директория с документами (PDF, DOCX, MD)"),
    output: Path = typer.Option(None, help="Куда сохранить JSON результат (опционально)"),
    save_to_db: bool = typer.Option(False, "--db", help="Сохранить векторы в PostgreSQL")
) -> None:
    """Сканирует директорию, парсит документы и (опционально) сохраняет в БД."""
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

    if output:
        processor.save_to_json(documents, output)
        console.print(f"[bold green]✓[/bold green] Сохранено в JSON: {output.absolute()}")

    if save_to_db:
        console.print("\n[bold yellow]Генерирую эмбеддинги и сохраняю в БД...[/bold yellow]")
        import asyncio
        
        async def _save_all():
            async with async_session_maker() as db:
                for doc in documents:
                    texts = [chunk.text for chunk in doc.chunks]
                    embeddings = embedding_service.embed_passages(texts)
                    path = Path(doc.metadata.source_path)
                    content_hash = compute_content_hash(
                        path.suffix.lower(), path.read_bytes()
                    )
                    await DocumentRepository.save_parsed_document(
                        db,
                        doc,
                        embeddings,
                        content_hash=content_hash,
                        file_size=f"{path.stat().st_size / (1024 * 1024):.2f} MB",
                    )
        
        asyncio.run(_save_all())
        console.print("[bold green]✓[/bold green] Успешно сохранено в PostgreSQL!")


if __name__ == "__main__":
    app()