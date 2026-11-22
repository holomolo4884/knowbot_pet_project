import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.document import Document, Chunk


class DocumentRepository:
    @staticmethod
    async def find_by_content_hash(
        db: AsyncSession, content_hash: str
    ) -> Document | None:
        result = await db.execute(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_with_chunks(db: AsyncSession, doc_id) -> bool:
        """Каскадно удаляет документ и все его чанки."""
        result = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return False
        await db.delete(doc)
        await db.commit()
        return True

    @staticmethod
    async def save_parsed_document(
        db: AsyncSession,
        parsed_doc,
        embeddings: list[list[float]],
        content_hash: str,
        file_size: str | None = None,
    ) -> tuple[Document, bool]:
        """Upsert по content_hash.

        Возвращает (document, was_created).
        При совпадении хеша удаляет старый документ и создаёт новый
        (свежие эмбеддинги могут отличаться от старых).
        """
        existing = await DocumentRepository.find_by_content_hash(db, content_hash)

        if existing:
            # Удаляем старый документ (каскадно удалятся чанки)
            await db.delete(existing)
            await db.flush()
            was_created = False
        else:
            was_created = True

        doc_id = uuid.UUID(parsed_doc.metadata.doc_id)

        db_doc = Document(
            id=doc_id,
            title=parsed_doc.metadata.title,
            source_path=parsed_doc.metadata.source_path,
            file_type=parsed_doc.metadata.file_type,
            content_hash=content_hash,
            file_size=file_size,
        )

        for chunk, vector in zip(parsed_doc.chunks, embeddings):
            db_doc.chunks.append(
                Chunk(
                    id=uuid.UUID(chunk.chunk_id),
                    document_id=doc_id,
                    text=chunk.text,
                    embedding=vector,
                    metadata_={
                        "title": chunk.title,
                        "section_path": chunk.section_path,
                        "page_number": chunk.page_number,
                    },
                )
            )

        db.add(db_doc)
        await db.flush()
        await db.commit()
        logger.info(
            f"{'Created' if was_created else 'Replaced'} '{db_doc.title}' "
            f"({db_doc.file_type}) with {len(db_doc.chunks)} chunks"
        )
        return db_doc, was_created