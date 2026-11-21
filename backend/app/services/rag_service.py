import time

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.retrieval.retriever import Retriever
from app.services.citation_validator import strip_invalid_markers, validate_citations
from app.services.llm_service import llm_service
from app.services.prompt import ABSTAIN_ANSWER, SYSTEM_PROMPT, build_user_prompt
from app.services.rag_schemas import ChatRequest, ChatResponse, Citation


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