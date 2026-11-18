import time
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Chunk, Document
from app.retrieval.schemas import RetrievedChunk
from app.services.embedding_service import embedding_service


class Retriever:
    """Векторный поиск по pgvector с фильтрами по метаданным."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        query: str,
        top_k: int = 5,
        doc_id: str | None = None,
        file_type: str | None = None,
    ) -> tuple[list[RetrievedChunk], float]:
        started = time.perf_counter()

        query_vector = embedding_service.embed_query(query)

        # <=> это cosine distance (0 = идентичны). Сходство = 1 - distance.
        distance = Chunk.embedding.cosine_distance(query_vector)
        score = (1 - distance).label("score")

        stmt = (
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.text,
                Chunk.metadata_,
                Document.title,
                score,
            )
            .join(Document, Document.id == Chunk.document_id)
            .order_by(distance)
            .limit(top_k)
        )

        if doc_id:
            stmt = stmt.where(Chunk.document_id == UUID(doc_id))
        if file_type:
            stmt = stmt.where(Document.file_type == file_type)

        rows = (await self.db.execute(stmt)).all()

        results = [
            RetrievedChunk(
                chunk_id=str(r.id),
                doc_id=str(r.document_id),
                text=r.text,
                title=r.title,
                section_path=(r.metadata_ or {}).get("section_path"),
                page_number=(r.metadata_ or {}).get("page_number"),
                score=round(float(r.score), 4),
            )
            for r in rows
        ]

        took_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(f"search '{query[:60]}' -> {len(results)} hits in {took_ms} ms")
        return results, took_ms