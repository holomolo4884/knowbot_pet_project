from app.retrieval.schemas import RetrievedChunk
from app.retrieval.context_filter import select_context


def _c(score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="x", doc_id="y", text="t", title=None,
        section_path=None, page_number=None, score=score,
    )


def test_cuts_at_large_gap():
    # Реальный профиль вопроса «дни активного отдыха»
    chunks = [_c(s) for s in (0.8435, 0.8315, 0.8306, 0.7929, 0.7839)]
    assert len(select_context(chunks)) == 3


def test_keeps_all_when_dense():
    # Реальный профиль вопроса «какие видео» — разрыва нет
    chunks = [_c(s) for s in (0.8055, 0.8021, 0.7991, 0.7987, 0.7983)]
    assert len(select_context(chunks)) == 5


def test_respects_max_keep():
    chunks = [_c(0.9 - i * 0.001) for i in range(10)]
    assert len(select_context(chunks, max_keep=3)) == 3


def test_empty_input():
    assert select_context([]) == []