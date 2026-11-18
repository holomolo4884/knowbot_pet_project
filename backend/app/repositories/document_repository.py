import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.document import Document, Chunk
from app.ingestion.models import ParsedDocument as IngestionParsedDocument


class DocumentRepository:
    @staticmethod
    async def save_parsed_document(
        db: AsyncSession,
        parsed_doc: IngestionParsedDocument,
        embeddings: list[list[float]],
    ) -> None:
        if len(embeddings) != len(parsed_doc.chunks):
            raise ValueError(
                f"Embeddings count ({len(embeddings)}) != chunks count ({len(parsed_doc.chunks)})"
            )

        doc_id = uuid.UUID(parsed_doc.metadata.doc_id)

        db_doc = Document(
            id=doc_id,
            title=parsed_doc.metadata.title,
            source_path=parsed_doc.metadata.source_path,
            file_type=parsed_doc.metadata.file_type,
        )

        # Добавляем чанки В КОЛЛЕКЦИЮ родителя, а не отдельным add_all
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

        # Явно фиксируем родителя перед вставкой детей
        await db.flush()

        await db.commit()
        logger.info(
            f"Saved '{db_doc.title}' ({db_doc.file_type}) with {len(db_doc.chunks)} chunks"
        )