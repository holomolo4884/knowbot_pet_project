import asyncio
import time
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    DocumentListItem,
    ReindexResponse,
    RenameRequest,
    UploadResponse,
)
from app.core.database import async_session_maker, get_db
from app.ingestion.parsers.docx_parser import DOCXParser
from app.ingestion.parsers.markdown_parser import MarkdownParser
from app.ingestion.parsers.pdf_parser import PDFParser
from app.repositories.document_repository import DocumentRepository
from app.services.content_hash import compute_content_hash
from app.services.embedding_service import embedding_service
from app.services.file_storage import delete_upload, resolve_source, save_upload
from app.services.stream_protocol import sse

router = APIRouter(prefix="/admin/documents", tags=["admin"])

PARSERS = {
    ".md": MarkdownParser(),
    ".markdown": MarkdownParser(),
    ".docx": DOCXParser(),
    ".pdf": PDFParser(),
}

MAX_SIZE_MB = 20
EMBED_BATCH = 8


def _validate(filename: str | None, content: bytes) -> tuple[int, str] | None:
    """Единая валидация: (status, message) либо None."""
    if not filename:
        return 400, "Имя файла обязательно"
    ext = Path(filename).suffix.lower()
    if ext not in PARSERS:
        return 400, (
            f"Неподдерживаемый формат: {ext}. "
            f"Доступны: {', '.join(sorted(PARSERS))}"
        )
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        return 413, f"Файл слишком большой: {size_mb:.1f} МБ > {MAX_SIZE_MB} МБ"
    return None


def _item(doc, chunks: int) -> DocumentListItem:
    return DocumentListItem(
        doc_id=str(doc.id),
        title=doc.title,
        file_type=doc.file_type,
        file_size=doc.file_size,
        content_hash=doc.content_hash,
        chunks=chunks,
        created_at=doc.created_at,
        source_path=doc.source_path,
        stored=resolve_source(doc.source_path) is not None,
    )


@router.get("", response_model=list[DocumentListItem])
async def list_documents(db: AsyncSession = Depends(get_db)):
    rows = await DocumentRepository.list_with_counts(db)
    return [_item(doc, count) for doc, count in rows]


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    force: bool = False,
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    error = _validate(file.filename, content)
    if error:
        raise HTTPException(error[0], error[1])

    ext = Path(file.filename).suffix.lower()
    content_hash = compute_content_hash(ext, content)
    started = time.perf_counter()

    existing = None if force else await DocumentRepository.find_by_content_hash(db, content_hash)
    if existing:
        return UploadResponse(
            doc_id=str(existing.id),
            title=existing.title,
            file_type=existing.file_type or ext.lstrip("."),
            chunks=len(existing.chunks),
            was_created=False,
            took_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    stored = save_upload(content_hash, ext, content)
    parsed = await asyncio.to_thread(PARSERS[ext].parse, stored)
    if parsed.metadata.title == stored.stem:
        parsed.metadata.title = Path(file.filename).stem
    if title:
        parsed.metadata.title = title

    texts = [c.text for c in parsed.chunks]
    if not texts:
        raise HTTPException(422, "Файл не содержит извлекаемого текста")

    embeddings = await asyncio.to_thread(embedding_service.embed_passages, texts)
    doc, was_created = await DocumentRepository.save_parsed_document(
        db, parsed, embeddings,
        content_hash=content_hash,
        file_size=f"{len(content) / (1024 * 1024):.2f} MB",
        title_override=title,        
    )
    return UploadResponse(
        doc_id=str(doc.id),
        title=doc.title,
        file_type=doc.file_type or ext.lstrip("."),
        chunks=len(doc.chunks),
        was_created=was_created,
        took_ms=round((time.perf_counter() - started) * 1000, 2),
    )


@router.post("/upload/stream")
async def upload_document_stream(
    file: UploadFile = File(...),
    force: bool = False,
    title: str | None = Form(None),
):
    content = await file.read()
    filename = file.filename
    ext = Path(filename or "").suffix.lower()

    async def event_stream():
        started = time.perf_counter()
        try:
            error = _validate(filename, content)
            if error:
                yield sse("error", {"message": error[1]})
                yield sse("done", {})
                return

            size_mb = len(content) / (1024 * 1024)
            content_hash = compute_content_hash(ext, content)
            yield sse("phase", {
                "phase": "received", "pct": 10,
                "size_mb": round(size_mb, 3), "hash": content_hash[:8],
            })

            async with async_session_maker() as db:
                existing = (
                    None if force
                    else await DocumentRepository.find_by_content_hash(db, content_hash)
                )
                if existing:
                    yield sse("phase", {"phase": "duplicate", "pct": 100})
                    yield sse("done", {
                        "doc_id": str(existing.id),
                        "title": existing.title,
                        "file_type": existing.file_type or ext.lstrip("."),
                        "chunks": len(existing.chunks),
                        "was_created": False,
                        "took_ms": round((time.perf_counter() - started) * 1000, 2),
                    })
                    return

                yield sse("phase", {"phase": "parsing", "pct": 30})
                stored = save_upload(content_hash, ext, content)
                parsed = await asyncio.to_thread(PARSERS[ext].parse, stored)
                if parsed.metadata.title == stored.stem:
                    parsed.metadata.title = Path(filename).stem
                if title:
                    parsed.metadata.title = title

                texts = [c.text for c in parsed.chunks]
                if not texts:
                    yield sse("error", {"message": "Файл не содержит извлекаемого текста"})
                    yield sse("done", {})
                    return

                yield sse("phase", {"phase": "parsed", "pct": 40, "chunks_found": len(texts)})

                vectors: list[list[float]] = []
                for i in range(0, len(texts), EMBED_BATCH):
                    batch = texts[i : i + EMBED_BATCH]
                    vectors.extend(
                        await asyncio.to_thread(embedding_service.embed_passages, batch)
                    )
                    done = min(i + EMBED_BATCH, len(texts))
                    yield sse("phase", {
                        "phase": "embedding",
                        "pct": 40 + int(50 * done / len(texts)),
                        "done": done, "total": len(texts),
                    })

                yield sse("phase", {"phase": "saving", "pct": 95})
                doc, was_created = await DocumentRepository.save_parsed_document(
                    db, parsed, vectors,
                    content_hash=content_hash,
                    file_size=f"{size_mb:.2f} MB",
                    title_override=title,
                )
                yield sse("done", {
                    "doc_id": str(doc.id),
                    "title": doc.title,
                    "file_type": doc.file_type or ext.lstrip("."),
                    "chunks": len(doc.chunks),
                    "was_created": was_created,
                    "took_ms": round((time.perf_counter() - started) * 1000, 2),
                })
        except Exception as e:
            logger.exception("Upload stream failed")
            yield sse("error", {"message": str(e)})
            yield sse("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{doc_id}", response_model=DocumentListItem)
async def rename_document(
    doc_id: UUID,
    payload: RenameRequest,
    db: AsyncSession = Depends(get_db),
):
    new_title = payload.title.strip()
    if not new_title:
        raise HTTPException(422, "Название не может быть пустым")
    doc = await DocumentRepository.rename(db, doc_id, new_title)
    if doc is None:
        raise HTTPException(404, "Документ не найден")
    rows = await DocumentRepository.list_with_counts(db)
    count = next((c for d, c in rows if d.id == doc.id), 0)
    return _item(doc, count)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, db: AsyncSession = Depends(get_db)):
    doc = await DocumentRepository.get_by_id(db, doc_id)
    if doc is None:
        raise HTTPException(404, "Документ не найден")
    source_path = doc.source_path
    resolved = resolve_source(source_path)
    await DocumentRepository.delete_with_chunks(db, doc_id)
    if resolved:
        delete_upload(str(resolved))
    return None


@router.post("/{doc_id}/reindex", response_model=ReindexResponse)
async def reindex_document(doc_id: UUID, db: AsyncSession = Depends(get_db)):
    """Пересобирает чанки текущим парсером. Идентичность и титул сохраняются."""
    doc = await DocumentRepository.get_by_id(db, doc_id)
    if doc is None:
        raise HTTPException(404, "Документ не найден")

    path = resolve_source(doc.source_path)
    if path is None:
        raise HTTPException(
            409,
            "Исходный файл недоступен. Загрузите документ заново.",
        )

    ext = path.suffix.lower()
    parser = PARSERS.get(ext)
    if parser is None:
        raise HTTPException(400, f"Нет парсера для {ext}")

    started = time.perf_counter()
    content = path.read_bytes()
    content_hash = compute_content_hash(ext, content)

    parsed = await asyncio.to_thread(parser.parse, path)
    texts = [c.text for c in parsed.chunks]
    if not texts:
        raise HTTPException(422, "Файл не содержит извлекаемого текста")

    vectors = await asyncio.to_thread(embedding_service.embed_passages, texts)
    new_doc, _ = await DocumentRepository.save_parsed_document(
        db, parsed, vectors,
        content_hash=content_hash,
        file_size=f"{len(content) / (1024 * 1024):.2f} MB",
    )
    return ReindexResponse(
        doc_id=str(new_doc.id),
        title=new_doc.title,
        chunks=len(new_doc.chunks),
        took_ms=round((time.perf_counter() - started) * 1000, 2),
    )