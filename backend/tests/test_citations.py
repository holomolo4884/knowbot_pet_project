from app.services.citation_validator import (
    extract_citation_indices,
    strip_invalid_markers,
    validate_citations,
)


def test_extract_preserves_order_and_dedupes():
    assert extract_citation_indices("Первое [2], второе [1], снова [2].") == [2, 1]


def test_valid_citations_pass():
    valid, invalid = validate_citations("Пароль от 12 символов [1].", total_chunks=3)
    assert valid == [1]
    assert invalid == 0


def test_hallucinated_marker_detected():
    valid, invalid = validate_citations("Согласно [1] и [7].", total_chunks=2)
    assert valid == [1]
    assert invalid == 1


def test_strip_removes_only_invalid():
    cleaned = strip_invalid_markers("Факт [1] и выдумка [9].", total_chunks=2)
    assert "[9]" not in cleaned
    assert "[1]" in cleaned


def test_no_citations_means_empty():
    valid, invalid = validate_citations("Просто текст без ссылок.", total_chunks=5)
    assert valid == []
    assert invalid == 0