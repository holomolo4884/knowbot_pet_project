import pytest

from app.services.stream_protocol import CitationStreamFilter, sse


def test_valid_marker_passes():
    f = CitationStreamFilter(total_chunks=3)
    assert f.feed("Пароль от 12 символов [1].") == "Пароль от 12 символов [1]."
    assert f.indices == [1]
    assert f.invalid_count == 0


def test_hallucinated_marker_stripped():
    f = CitationStreamFilter(total_chunks=2)
    assert f.feed("Факт [1] и выдумка [7].") == "Факт [1] и выдумка ."
    assert f.indices == [1]
    assert f.invalid_count == 1


def test_marker_split_across_chunks():
    f = CitationStreamFilter(total_chunks=2)
    parts = [
        f.feed("Пар"),
        f.feed("оль ["),
        f.feed("1] готово"),
    ]
    assert parts == ["Пар", "оль ", "[1] готово"]
    assert "".join(parts) == "Пароль [1] готово"
    assert f.indices == [1]


def test_non_citation_brackets_preserved():
    f = CitationStreamFilter(total_chunks=2)
    assert f.feed("Список [abc] и [см. выше].") == "Список [abc] и [см. выше]."
    assert f.indices == []


def test_dedupes_repeated_markers():
    f = CitationStreamFilter(total_chunks=3)
    f.feed("Первое [2], второе [1], снова [2].")
    assert f.indices == [2, 1]


def test_flush_returns_unfinished_tail():
    f = CitationStreamFilter(total_chunks=2)
    f.feed("Текст [1")
    assert f.flush() == "[1"


def test_sse_frame_format():
    frame = sse("delta", {"text": "привет"})
    assert frame.startswith("event: delta\n")
    assert "привет" in frame
    assert frame.endswith("\n\n")


@pytest.mark.parametrize("split_at", range(1, len("Пароль [1] готово")))
def test_marker_survives_any_split(split_at):
    """Фильтр инвариантен к месту разрыва потока — проверяем каждую границу."""
    text = "Пароль [1] готово"
    f = CitationStreamFilter(total_chunks=2)
    out = f.feed(text[:split_at]) + f.feed(text[split_at:]) + f.flush()
    assert out == text
    assert f.indices == [1]