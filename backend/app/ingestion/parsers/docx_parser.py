from pathlib import Path

from docx import Document
from loguru import logger

from ..models import Chunk, DocumentMetadata, ParsedDocument


class DOCXParser:
    """Парсер DOCX с иерархией Title -> Heading N."""

    TITLE_STYLES = {"title", "название", "subtitle", "подзаголовок"}

    def parse(self, file_path: Path) -> ParsedDocument:
        logger.info(f"Parsing DOCX: {file_path.name}")
        doc = Document(file_path)

        metadata = DocumentMetadata(
            title=file_path.stem,
            source_path=str(file_path),
            file_type="docx",
        )

        chunks: list[Chunk] = []
        section_path: list[str] = []
        text_parts: list[str] = []
        title_offset = 0  # 1, если корень иерархии — Title

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style = (para.style.name or "").lower()

            # Title — корень дерева, а не отдельный чанк
            if style in self.TITLE_STYLES:
                if text_parts:
                    chunks.append(self._make_chunk(text_parts, metadata.doc_id, section_path))
                    text_parts = []
                section_path = [text]
                title_offset = 1
                metadata.title = text
                continue

            if style.startswith("heading") or style.startswith("заголовок"):
                if text_parts:
                    chunks.append(self._make_chunk(text_parts, metadata.doc_id, section_path))
                    text_parts = []
                level = self._heading_level(style)
                keep = title_offset + level - 1
                section_path = section_path[:keep] + [text]
                continue

            text_parts.append(text)

        if text_parts:
            chunks.append(self._make_chunk(text_parts, metadata.doc_id, section_path))

        return ParsedDocument(metadata=metadata, chunks=chunks)

    @staticmethod
    def _heading_level(style: str) -> int:
        digits = "".join(ch for ch in style if ch.isdigit())
        return int(digits) if digits else 1

    def _make_chunk(
        self, parts: list[str], doc_id: str, section_path: list[str]
    ) -> Chunk:
        return Chunk(
            text=" ".join(parts),
            doc_id=doc_id,
            title=section_path[0] if section_path else "Без названия",
            section_path=" > ".join(section_path) if section_path else "Общий раздел",
            page_number=None,
        )