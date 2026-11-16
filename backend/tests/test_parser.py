import pytest
from pathlib import Path
from app.ingestion.parsers.pdf_parser import PDFParser
from app.ingestion.parsers.docx_parser import DOCXParser
from app.ingestion.parsers.markdown_parser import MarkdownParser
from docx import Document
import pymupdf as fitz

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

def test_pdf_parser(temp_dir):
    # 1. Создаем тестовый PDF
    pdf_path = temp_dir / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "MAIN HEADING", fontsize=16)
    page.insert_text((50, 100), "This is regular text for testing the parser logic.", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    # 2. Парсим
    parser = PDFParser()
    result = parser.parse(pdf_path)

    # 3. Ассерты
    assert result.metadata.file_type == "pdf"
    assert len(result.chunks) >= 1
    assert "MAIN HEADING" in result.chunks[0].section_path
    assert "his is regular text for testing the parser logic." in result.chunks[-1].text

def test_docx_parser(temp_dir):
    # 1. Создаем тестовый DOCX
    docx_path = temp_dir / "test.docx"
    doc = Document()
    doc.add_heading('Главный раздел', level=1)
    doc.add_paragraph('Это текст первого абзаца.')
    doc.add_heading('Подраздел', level=2)
    doc.add_paragraph('Текст подраздела.')
    doc.save(docx_path)

    # 2. Парсим
    parser = DOCXParser()
    result = parser.parse(docx_path)

    # 3. Ассерты
    assert result.metadata.file_type == "docx"
    assert len(result.chunks) == 2 # Один для главного раздела, один для подраздела
    assert result.chunks[0].section_path == "Главный раздел"
    assert result.chunks[1].section_path == "Главный раздел > Подраздел"

def test_markdown_parser(temp_dir):
    # 1. Создаем тестовый MD
    md_path = temp_dir / "test.md"
    md_content = "# Заголовок 1\nТекст под заголовком 1.\n\n## Заголовок 2\nТекст под заголовком 2."
    md_path.write_text(md_content, encoding='utf-8')

    # 2. Парсим
    parser = MarkdownParser()
    result = parser.parse(md_path)

    # 3. Ассерты
    assert result.metadata.file_type == "md"
    assert len(result.chunks) == 2
    assert result.chunks[0].section_path == "Заголовок 1"
    assert result.chunks[1].section_path == "Заголовок 1 > Заголовок 2"