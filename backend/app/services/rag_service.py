import time

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import AsyncIterator

from app.core.config import settings
from app.retrieval.retriever import Retriever
from app.services.citation_validator import strip_invalid_markers, validate_citations
from app.services.llm_service import llm_service
from app.services.prompt import ABSTAIN_ANSWER, SYSTEM_PROMPT, build_user_prompt, STREAM_SYSTEM_PROMPT
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

        # Guardrail 1: не зовём LLM на нерелевантном контексте
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

        started = time.perf_counter()
        raw = await llm_service.complete_json(
            system=SYSTEM_PROMPT,
            user=build_user_prompt(req.question, chunks),
        )
        generation_ms = round((time.perf_counter() - started) * 1000, 2)

        answer_text = str(raw.get("answer", "")).strip() or ABSTAIN_ANSWER

        # Guardrail 2: сверяем маркеры [N] с реальным числом фрагментов
        valid_indices, invalid_count = validate_citations(answer_text, len(chunks))
        if invalid_count:
            logger.warning(f"{invalid_count} hallucinated citation markers removed")
            answer_text = strip_invalid_markers(answer_text, len(chunks))

        abstained = answer_text == ABSTAIN_ANSWER
        citations = [
            Citation(
                index=i,
                chunk_id=chunks[i - 1].chunk_id,
                doc_id=chunks[i - 1].doc_id,
                title=chunks[i - 1].title,
                section_path=chunks[i - 1].section_path,
                page_number=chunks[i - 1].page_number,
                score=chunks[i - 1].score,
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

        yield sse("retrieval", {
            "hits": len(chunks),
            "best_score": round(best_score, 4),
            "took_ms": retrieval_ms,
        })

        # Guardrail 1: тот же порог, что и в /chat — LLM не вызываем
        if not chunks or best_score < settings.MIN_RELEVANCE_SCORE:
            logger.info(f"Stream abstain: best_score={best_score:.4f}")
            yield sse("delta", {"text": ABSTAIN_ANSWER})
            yield sse("citations", {"items": []})
            yield sse("meta", {
                "grounded": False,
                "abstained": True,
                "invalid_citation_markers": 0,
                "retrieval_ms": retrieval_ms,
                "generation_ms": 0.0,
                "model": "none",
            })
            yield sse("done", {})
            return

        filt = CitationStreamFilter(len(chunks))
        full_text_parts: list[str] = []
        started = time.perf_counter()

        try:
            async for piece in llm_service.stream_text(
                system=STREAM_SYSTEM_PROMPT,
                user=build_user_prompt(req.question, chunks),
            ):
                safe = filt.feed(piece)
                if safe:
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
                chunk_id=chunks[i - 1].chunk_id,
                doc_id=chunks[i - 1].doc_id,
                title=chunks[i - 1].title,
                section_path=chunks[i - 1].section_path,
                page_number=chunks[i - 1].page_number,
                score=chunks[i - 1].score,
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
            "generation_ms": generation_ms,
            "model": llm_service.model,
        })
        yield sse("done", {})