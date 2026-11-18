import pytest
from unittest.mock import MagicMock

from app.retrieval.retriever import Retriever
from app.retrieval.schemas import RetrievedChunk


@pytest.mark.asyncio
async def test_search_returns_ranked_chunks(monkeypatch):
    """Retriever корректно мапит строки БД в схему и считает score."""
    fake_rows = [
        MagicMock(
            id="11111111-1111-1111-1111-111111111111",
            document_id="22222222-2222-2222-2222-222222222222",
            text="Пароль должен содержать не менее 12 символов.",
            metadata_={"section_path": "Политика > Пароли", "page_number": None},
            title="security_policy",
            score=0.87,
        ),
        MagicMock(
            id="33333333-3333-3333-3333-333333333333",
            document_id="22222222-2222-2222-2222-222222222222",
            text="Заявление на отпуск подается за 2 недели.",
            metadata_={"section_path": "HR > Отпуска", "page_number": None},
            title="hr_policy",
            score=0.41,
        ),
    ]

    db = MagicMock()
    exec_result = MagicMock()
    exec_result.all.return_value = fake_rows

    async def fake_execute(stmt):
        return exec_result

    db.execute = fake_execute

    monkeypatch.setattr(
        "app.retrieval.retriever.embedding_service.embed_query",
        lambda q: [0.0] * 1024,
    )

    results, took_ms = await Retriever(db).search("пароль", top_k=2)

    assert len(results) == 2
    assert all(isinstance(r, RetrievedChunk) for r in results)
    assert results[0].score > results[1].score
    assert results[0].section_path == "Политика > Пароли"
    assert took_ms >= 0


@pytest.mark.asyncio
async def test_empty_result(monkeypatch):
    db = MagicMock()
    exec_result = MagicMock()
    exec_result.all.return_value = []

    async def fake_execute(stmt):
        return exec_result

    db.execute = fake_execute
    monkeypatch.setattr(
        "app.retrieval.retriever.embedding_service.embed_query",
        lambda q: [0.0] * 1024,
    )

    results, _ = await Retriever(db).search("что угодно")
    assert results == []