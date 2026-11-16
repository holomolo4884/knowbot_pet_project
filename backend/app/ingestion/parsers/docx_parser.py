from docx import Document
from pathlib import Path
from loguru import logger
from ..models import DocumentMetadata, Chunk, ParsedDocument

class DOCXParser:
    def parse(self, file_path: Path) -> ParsedDocument:
        logger.info(f"Parsing DOCX: {file_path.name}")
        doc = Document(file_path)
        
        metadata = DocumentMetadata(
            title=file_path.stem,
            source_path=str(file_path),
            file_type="docx"
        )
        
        chunks = []
        current_section_path = []
        current_text_parts = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Проверка стиля заголовка в Word
            style_name = para.style.name.lower()
            is_heading = style_name.startswith('heading') or style_name.startswith('заголовок')
            
            if is_heading:
                if current_text_parts:
                    chunks.append(self._make_chunk(current_text_parts, metadata.doc_id, current_section_path))
                    current_text_parts = []
                
                level = 1
                for char in style_name:
                    if char.isdigit():
                        level = int(char)
                        break
                
                current_section_path = current_section_path[:level-1] + [text]
            else:
                current_text_parts.append(text)
                
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