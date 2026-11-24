from pathlib import Path

from app.ingestion.parsers.markdown_parser import MarkdownParser


def _parse(tmp_path: Path, text: str):
    f = tmp_path / "doc.md"
    f.write_text(text, encoding="utf-8")
    return MarkdownParser().parse(f)


def test_same_level_headings_are_siblings(tmp_path):
    doc = _parse(tmp_path, "## Неделя 1\nтекст1\n## Неделя 2\nтекст2\n")
    paths = [c.section_path for c in doc.chunks]
    assert paths == ["Неделя 2", "Неделя 1"] or paths == ["Неделя 1", "Неделя 2"]
    assert all(" > " not in p for p in paths)


def test_nested_headings_keep_hierarchy(tmp_path):
    doc = _parse(tmp_path, "# Раздел\n## Подраздел\nтекст\n")
    assert doc.chunks[0].section_path == "Раздел > Подраздел"


def test_bold_line_becomes_pseudo_heading(tmp_path):
    doc = _parse(tmp_path, "## Неделя 1\n**Пн, 4 мая**\nдело1\n**Вт, 5 мая**\nдело2\n")
    paths = [c.section_path for c in doc.chunks]
    assert "Неделя 1 > Пн, 4 мая" in paths
    assert "Неделя 1 > Вт, 5 мая" in paths


def test_bold_with_trailing_text_is_not_heading(tmp_path):
    doc = _parse(tmp_path, "## Раздел\n**Конспект:** длинный текст дальше\n")
    assert len(doc.chunks) == 1
    assert "Конспект" in doc.chunks[0].text


def test_long_section_is_split(tmp_path):
    body = "\n".join([f"Строка номер {i} с достаточным количеством текста." for i in range(120)])
    doc = _parse(tmp_path, f"## Раздел\n{body}\n")
    assert len(doc.chunks) > 1
    assert all(len(c.text) <= 1400 for c in doc.chunks)


def test_no_headings_falls_back_to_general_section(tmp_path):
    doc = _parse(tmp_path, "просто текст без разметки\nвторая строка\n")
    assert doc.chunks[0].section_path == "Общий раздел"


def test_h1_becomes_document_title(tmp_path):
    doc = _parse(tmp_path, "# Человекочитаемый заголовок\nтекст\n")
    assert doc.metadata.title == "Человекочитаемый заголовок"


def test_no_h1_keeps_filename_title(tmp_path):
    doc = _parse(tmp_path, "## Только подзаголовок\nтекст\n")
    assert doc.metadata.title == "doc"