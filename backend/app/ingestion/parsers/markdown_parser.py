from markdown_it import MarkdownIt
from pathlib import Path
from loguru import logger
from ..models import DocumentMetadata, Chunk, ParsedDocument

class MarkdownParser:
    def __init__(self):
        self.md = MarkdownIt()

    def parse(self, file_path: Path) -> ParsedDocument:
        logger.info(f"Parsing Markdown: {file_path.name}")
        content = file_path.read_text(encoding='utf-8')
        tokens = self.md.parse(content)
        
        metadata = DocumentMetadata(
            title=file_path.stem,
            source_path=str(file_path),
            file_type="md"
        )
        
        chunks = []
        current_section_path = []
        current_text_parts = []
        
        for i, token in enumerate(tokens):
            if token.type == 'heading_open':
                if current_text_parts:
                    chunks.append(self._make_chunk(current_text_parts, metadata.doc_id, current_section_path))
                    current_text_parts = []
                
                level = int(token.tag[1])
                # Следующий токен содержит текст заголовка
                if i + 1 < len(tokens) and tokens[i+1].type == 'inline':
                    heading_text = tokens[i+1].content.strip()
                    current_section_path = current_section_path[:level-1] + [heading_text]
            elif token.type == 'inline' and token.content.strip():
                # Пропускаем, если это заголовок (он уже обработан)
                if i > 0 and tokens[i-1].type == 'heading_open':
                    continue
                current_text_parts.append(token.content.strip())
                
        if current_text_parts:
            chunks.append(self._make_chunk(current_text_parts, metadata.doc_id, current_section_path))
            
        return ParsedDocument(metadata=metadata, chunks=chunks)

    def _make_chunk(self, text_parts: list[str], doc_id: str, section_path: list[str]) -> Chunk:
        return Chunk(
            text=" ".join(text_parts),
            doc_id=doc_id,
            title=section_path[0] if section_path else "Без названия",
            section_path=" > ".join(section_path) if section_path else "Общий раздел",
            page_number=None
        )