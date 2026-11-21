from unittest.mock import AsyncMock, MagicMock

import pytest

from app.retrieval.schemas import RetrievedChunk
from app.services.rag_schemas import ChatRequest
from app.services.rag_service import RAGService


def _chunk(score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="11111111-1111-1111-1111-111111111111",
        doc_id="22222222-2222-2222-2222-222222222222",
        text="Пароль должен содержать не менее 12 символов.",
        title="security_policy",
        section_path="Политика > Пароли",
        page_number=None,
        score=score,
    )


@pytest.mark.asyncio
async def test_abstains_without_llm_call(monkeypatch):
    service = RAGService(MagicMock())
    service.retriever.search = AsyncMock(return_value=([_chunk(0.50)], 10.0))

    llm_mock = AsyncMock()
    monkeypatch.setattr("app.services.rag_service.llm_service.complete_json", llm_mock)

    res = await service.answer(ChatRequest(question="погода на Марсе"))

    assert res.abstained is True
    assert res.grounded is False
    assert res.citations == []
    assert res.model == "none"
    llm_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_grounded_answer_with_citation(monkeypatch):
    service = RAGService(MagicMock())
    service.retriever.search = AsyncMock(return_value=([_chunk(0.88)], 12.0))

    monkeypatch.setattr(
        "app.services.rag_service.llm_service.complete_json",
        AsyncMock(return_value={"answer": "Минимум 12 символов [1].", "citations": [1]}),
    )

    res = await service.answer(ChatRequest(question="длина пароля"))

    assert res.grounded is True
    assert res.abstained is False
    assert len(res.citations) == 1
    assert res.citations[0].section_path == "Политика > Пароли"


@pytest.mark.asyncio
async def test_hallucinated_marker_is_stripped(monkeypatch):
    service = RAGService(MagicMock())
    service.retriever.search = AsyncMock(return_value=([_chunk(0.88)], 12.0))

    monkeypatch.setattr(
        "app.services.rag_service.llm_service.complete_json",
        AsyncMock(return_value={"answer": "12 символов [1] и ещё факт [5]."}),
    )

    res = await service.answer(ChatRequest(question="длина пароля"))

    assert res.invalid_citation_markers == 1
    assert "[5]" not in res.answer
    assert len(res.citations) == 1