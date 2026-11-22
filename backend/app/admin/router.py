import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ingestion.parsers.docx_parser import DOCXParser
from app.ingestion.parsers.markdown_parser import MarkdownParser
from app.ingestion.parsers.pdf_parser import PDFParser
from app.repositories.document_repository import DocumentRepository
from app.services.content_hash import compute_content_hash
from app.services.embedding_service import embedding_service

router = APIRouter(prefix="/admin/documents", tags=["admin"])

PARSERS = {
    ".md": MarkdownParser(),
    ".markdown": MarkdownParser(),
    ".docx": DOCXParser(),
    ".pdf": PDFParser(),
}

MAX_SIZE_MB = 20


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
    existing = await DocumentRepository.find_by_content_hash(db, content_hash)
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