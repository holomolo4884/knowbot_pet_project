import re

CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def extract_citation_indices(answer: str) -> list[int]:
    """Номера [N] в порядке первого появления, без дублей."""
    seen: dict[int, None] = {}
    for match in CITATION_PATTERN.finditer(answer):
        seen.setdefault(int(match.group(1)), None)
    return list(seen)


def validate_citations(answer: str, total_chunks: int) -> tuple[list[int], int]:
    """(валидные индексы, число невалидных маркеров).

    Невалидный маркер = ссылка на несуществующий фрагмент = галлюцинация.
    """
    indices = extract_citation_indices(answer)
    valid = [i for i in indices if 1 <= i <= total_chunks]
    return valid, len(indices) - len(valid)


def strip_invalid_markers(answer: str, total_chunks: int) -> str:
    def repl(match: re.Match) -> str:
        n = int(match.group(1))
        return match.group(0) if 1 <= n <= total_chunks else ""

    return CITATION_PATTERN.sub(repl, answer).strip()