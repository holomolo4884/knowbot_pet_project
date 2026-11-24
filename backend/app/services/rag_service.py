import time
from collections.abc import AsyncIterator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.retrieval.context_filter import select_context
from app.retrieval.retriever import Retriever
from app.services.citation_validator import strip_invalid_markers, validate_citations
from app.services.llm_service import llm_service
from app.services.prompt import (
    ABSTAIN_ANSWER,
    STREAM_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.services.rag_schemas import ChatRequest, ChatResponse, Citation
from app.services.stream_protocol import CitationStreamFilter, sse


class RAGService:
    def __init__(self, db: AsyncSession) -> None:
        self.retriever = Retriever(db)

    async def answer(self, req: ChatRequest) -> ChatResponse:
        chunks, retrieval_ms = await self.retriever.search(
            query=req.question,
            top_k=req.top_k,
            doc_id=req.doc_id,
            file_type=req.file_type,
        )
        best_score = max((c.score for c in chunks), default=0.0)

        # Guardrail 1: абсолютный floor — отвечать ли вообще
        if not chunks or best_score < settings.MIN_RELEVANCE_SCORE:
            logger.info(f"Abstain: best_score={best_score:.4f} < {settings.MIN_RELEVANCE_SCORE}")
            return ChatResponse(
                question=req.question,
                answer=ABSTAIN_ANSWER,
                citations=[],
                grounded=False,
                abstained=True,
                retrieval_ms=retrieval_ms,
                generation_ms=0.0,
                model="none",
            )

        # Отбор контекста по разрыву в score, а не по абсолютному порогу
        context_chunks = select_context(chunks)
        logger.debug(
            f"Context: {len(context_chunks)}/{len(chunks)} chunks, best={best_score:.4f}"
        )

        started = time.perf_counter()
        raw = await llm_service.complete_json(
            system=SYSTEM_PROMPT,
            user=build_user_prompt(req.question, context_chunks),
        )
        generation_ms = round((time.perf_counter() - started) * 1000, 2)

        answer_text = str(raw.get("answer", "")).strip() or ABSTAIN_ANSWER

        # Guardrail 2: маркеры сверяем с числом фрагментов, ушедших в промпт
        valid_indices, invalid_count = validate_citations(answer_text, len(context_chunks))
        if invalid_count:
            logger.warning(f"{invalid_count} hallucinated citation markers removed")
            answer_text = strip_invalid_markers(answer_text, len(context_chunks))

        abstained = answer_text == ABSTAIN_ANSWER
        citations = [
            Citation(
                index=i,
                chunk_id=context_chunks[i - 1].chunk_id,
                doc_id=context_chunks[i - 1].doc_id,
                title=context_chunks[i - 1].title,
                section_path=context_chunks[i - 1].section_path,
                page_number=context_chunks[i - 1].page_number,
                score=context_chunks[i - 1].score,
            )
            for i in valid_indices
        ]

        return ChatResponse(
            question=req.question,
            answer=answer_text,
            citations=citations,
            grounded=bool(citations) and not abstained,
            abstained=abstained,
            invalid_citation_markers=invalid_count,
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            model=llm_service.model,
        )

    async def answer_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        """Стримит ответ по SSE. Цитаты валидируются на лету."""
        chunks, retrieval_ms = await self.retriever.search(
            query=req.question,
            top_k=req.top_k,
            doc_id=req.doc_id,
            file_type=req.file_type,
        )
        best_score = max((c.score for c in chunks), default=0.0)
        context_chunks = select_context(chunks)

        yield sse("retrieval", {
            "hits": len(chunks),
            "context_hits": len(context_chunks),
            "best_score": round(best_score, 4),
            "took_ms": retrieval_ms,
        })

        # Guardrail 1: абсолютный floor — LLM не вызываем
        if not chunks or best_score < settings.MIN_RELEVANCE_SCORE:
            logger.info(f"Stream abstain: best_score={best_score:.4f}")
            yield sse("delta", {"text": ABSTAIN_ANSWER})
            yield sse("citations", {"items": []})
            yield sse("meta", {
                "grounded": False,
                "abstained": True,
                "invalid_citation_markers": 0,
                "retrieval_ms": retrieval_ms,
                "ttft_ms": 0.0,
                "generation_ms": 0.0,
                "model": "none",
            })
            yield sse("done", {})
            return

        logger.debug(
            f"Stream context: {len(context_chunks)}/{len(chunks)}, best={best_score:.4f}"
        )

        filt = CitationStreamFilter(len(context_chunks))
        full_text_parts: list[str] = []
        ttft_ms: float | None = None
        started = time.perf_counter()

        try:
            async for piece in llm_service.stream_text(
                system=STREAM_SYSTEM_PROMPT,
                user=build_user_prompt(req.question, context_chunks),
            ):
                safe = filt.feed(piece)
                if safe:
                    if ttft_ms is None:
                        ttft_ms = round((time.perf_counter() - started) * 1000, 2)
                    full_text_parts.append(safe)
                    yield sse("delta", {"text": safe})

            tail = filt.flush()
            if tail:
                full_text_parts.append(tail)
                yield sse("delta", {"text": tail})

        except Exception as e:
            logger.exception("Stream generation failed")
            yield sse("error", {"message": str(e)})
            yield sse("done", {})
            return

        generation_ms = round((time.perf_counter() - started) * 1000, 2)
        full_text = "".join(full_text_parts)
        abstained = ABSTAIN_ANSWER.lower() in full_text.lower()

        citations = [
            Citation(
                index=i,
                chunk_id=context_chunks[i - 1].chunk_id,
                doc_id=context_chunks[i - 1].doc_id,
                title=context_chunks[i - 1].title,
                section_path=context_chunks[i - 1].section_path,
                page_number=context_chunks[i - 1].page_number,
                score=context_chunks[i - 1].score,
            ).model_dump()
            for i in filt.indices
        ]

        if filt.invalid_count:
            logger.warning(f"Stream: {filt.invalid_count} hallucinated markers stripped")

        yield sse("citations", {"items": citations})
        yield sse("meta", {
            "grounded": bool(citations) and not abstained,
            "abstained": abstained,
            "invalid_citation_markers": filt.invalid_count,
            "retrieval_ms": retrieval_ms,
            "ttft_ms": ttft_ms,
            "generation_ms": generation_ms,
            "model": llm_service.model,
        })
        yield sse("done", {})