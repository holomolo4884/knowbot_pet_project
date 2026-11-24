import re
from pathlib import Path

from loguru import logger

from ..models import Chunk, DocumentMetadata, ParsedDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BOLD_LINE_RE = re.compile(r"^\*\*(.+?)\*\*:?\s*$")

MAX_CHARS = 1200
OVERLAP = 150
MAX_PSEUDO_HEADING_LEN = 80


class MarkdownParser:
    """Markdown с корректной иерархией и фолбэк-чанкингом.

    - Уровни заголовков ведутся стеком, а не срезом: соседи одного уровня
      замещают друг друга, а не вкладываются.
    - Строка целиком из **bold** трактуется как псевдо-заголовок на уровень глубже.
      Реальные документы часто структурированы визуально, а не разметкой.
    - Секции длиннее MAX_CHARS режутся по строкам с перекрытием.
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        logger.info(f"Parsing Markdown: {file_path.name}")
        lines = file_path.read_text(encoding="utf-8").splitlines()

        metadata = DocumentMetadata(
            title=file_path.stem,
            source_path=str(file_path),
            file_type="md",
        )

        chunks: list[Chunk] = []
        stack: list[tuple[int, str]] = []
        buf: list[str] = []
        heading_level = 0

        def current_path() -> list[str]:
            return [title for _, title in stack]

        def flush() -> None:
            nonlocal buf
            if not buf:
                return
            text = "\n".join(buf).strip()
            buf = []
            if text:
                chunks.extend(self._split(text, metadata.doc_id, current_path()))

        def push(level: int, title: str) -> None:
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))

        for raw_line in lines:
            line = raw_line.strip()

            if not line:
                buf.append("")
                continue

            heading = HEADING_RE.match(line)
            if heading:
                flush()
                heading_level = len(heading.group(1))
                title = heading.group(2).strip()
                push(heading_level, title)
                if heading_level == 1 and metadata.title == file_path.stem:
                    metadata.title = title
                continue

            bold = BOLD_LINE_RE.match(line)
            if bold and len(line) <= MAX_PSEUDO_HEADING_LEN:
                flush()
                push(heading_level + 1, bold.group(1).strip().rstrip(":"))
                continue

            buf.append(line)

        flush()
        logger.info(f"Parsed {file_path.name}: {len(chunks)} chunks")
        return ParsedDocument(metadata=metadata, chunks=chunks)

    def _split(self, text: str, doc_id: str, path: list[str]) -> list[Chunk]:
        section = " > ".join(path) if path else "Общий раздел"
        title = path[0] if path else "Без названия"

        if len(text) <= MAX_CHARS:
            return [
                Chunk(
                    text=text,
                    doc_id=doc_id,
                    title=title,
                    section_path=section,
                    page_number=None,
                )
            ]

        parts: list[str] = []
        buf = ""
        for line in text.split("\n"):
            if buf and len(buf) + len(line) + 1 > MAX_CHARS:
                parts.append(buf.strip())
                tail = buf[-OVERLAP:] if OVERLAP else ""
                buf = f"{tail}\n{line}" if tail else line
            else:
                buf = f"{buf}\n{line}" if buf else line
        if buf.strip():
            parts.append(buf.strip())

        return [
            Chunk(
                text=part,
                doc_id=doc_id,
                title=title,
                section_path=section,
                page_number=None,
            )
            for part in parts
        ]