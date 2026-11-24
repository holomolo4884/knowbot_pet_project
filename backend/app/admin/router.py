import time
import uuid
from pathlib import Path
import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session_maker
from app.ingestion.parsers.docx_parser import DOCXParser
from app.ingestion.parsers.markdown_parser import MarkdownParser
from app.ingestion.parsers.pdf_parser import PDFParser
from app.repositories.document_repository import DocumentRepository
from app.services.content_hash import compute_content_hash
from app.services.embedding_service import embedding_service
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


class UploadResponse(BaseModel):
    doc_id: str
    title: str
    file_type: str
    chunks: int
    was_created: bool
    took_ms: float


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Загружает файл, парсит, индексирует. Идемпотентно по content_hash."""
    if not file.filename:
        raise HTTPException(400, "Имя файла обязательно")

    ext = Path(file.filename).suffix.lower()
    parser = PARSERS.get(ext)
    if parser is None:
        raise HTTPException(
            400,
            f"Неподдерживаемый формат: {ext}. "
            f"Доступны: {', '.join(sorted(PARSERS))}",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(413, f"Файл слишком большой: {size_mb:.1f} МБ > {MAX_SIZE_MB} МБ")

    content_hash = compute_content_hash(ext, content)
    started = time.perf_counter()

    # Проверка: может, этот файл уже загружен?
    existing = None if force else await DocumentRepository.find_by_content_hash(db, content_hash)
    if existing:
        took_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(f"Файл уже загружен (id={existing.id}), возвращаем существующий")
        return UploadResponse(
            doc_id=str(existing.id),
            title=existing.title,
            file_type=existing.file_type or ext.lstrip("."),
            chunks=len(existing.chunks) if existing.chunks else 0,
            was_created=False,
            took_ms=took_ms,
        )

    # Сохраняем во временный файл для парсеров (они ждут Path)
    tmp_dir = Path("/tmp/knowbot_uploads")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4()}{ext}"

    try:
        tmp_path.write_bytes(content)
        parsed = parser.parse(tmp_path)
        if parsed.metadata.title == tmp_path.stem:
            parsed.metadata.title = Path(file.filename).stem

        texts = [c.text for c in parsed.chunks]
        if not texts:
            raise HTTPException(422, "Файл не содержит извлекаемого текста")

        embeddings = embedding_service.embed_passages(texts)

        doc, was_created = await DocumentRepository.save_parsed_document(
            db, parsed, embeddings, content_hash=content_hash,
            file_size=f"{size_mb:.2f} MB",
        )
        took_ms = round((time.perf_counter() - started) * 1000, 2)

        return UploadResponse(
            doc_id=str(doc.id),
            title=doc.title,
            file_type=doc.file_type or ext.lstrip("."),
            chunks=len(doc.chunks),
            was_created=was_created,
            took_ms=took_ms,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/upload/stream")
async def upload_document_stream(file: UploadFile = File(...), force: bool = False):
    """Загрузка с SSE-прогрессом: received -> parsing -> embedding* -> saving -> done."""
    # Читаем ДО генератора: UploadFile закроется к моменту стриминга
    content = await file.read()
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    async def event_stream():
        started = time.perf_counter()
        tmp_path: Path | None = None

        try:
            parser = PARSERS.get(ext)
            if parser is None:
                yield sse("error", {"message": f"Неподдерживаемый формат: {ext}"})
                yield sse("done", {})
                return

            size_mb = len(content) / (1024 * 1024)
            if size_mb > MAX_SIZE_MB:
                yield sse("error", {"message": f"Файл слишком большой: {size_mb:.1f} МБ"})
                yield sse("done", {})
                return

            content_hash = compute_content_hash(ext, content)
            yield sse("phase", {
                "phase": "received",
                "pct": 10,
                "size_mb": round(size_mb, 3),
                "hash": content_hash[:8],
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

                tmp_dir = Path("/tmp/knowbot_uploads")
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = tmp_dir / f"{uuid.uuid4()}{ext}"
                tmp_path.write_bytes(content)

                # CPU-bound парсинг не должен блокировать event loop
                parsed = await asyncio.to_thread(parser.parse, tmp_path)
                if parsed.metadata.title == tmp_path.stem:
                    parsed.metadata.title = Path(filename).stem

                texts = [c.text for c in parsed.chunks]
                if not texts:
                    yield sse("error", {"message": "Файл не содержит извлекаемого текста"})
                    yield sse("done", {})
                    return

                yield sse("phase", {
                    "phase": "parsed",
                    "pct": 40,
                    "chunks_found": len(texts),
                })

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
                        "done": done,
                        "total": len(texts),
                    })

                yield sse("phase", {"phase": "saving", "pct": 95})
                doc, was_created = await DocumentRepository.save_parsed_document(
                    db, parsed, vectors,
                    content_hash=content_hash,
                    file_size=f"{size_mb:.2f} MB",
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
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )