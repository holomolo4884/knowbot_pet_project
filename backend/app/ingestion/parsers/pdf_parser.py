import pymupdf as fitz
from pathlib import Path
from loguru import logger
from ..models import DocumentMetadata, Chunk, ParsedDocument

class PDFParser:
    def parse(self, file_path: Path) -> ParsedDocument:
        logger.info(f"Parsing PDF: {file_path.name}")
        doc = fitz.open(file_path)
        
        raw_title = (doc.metadata or {}).get("title") or ""
        title = raw_title.strip() or file_path.stem

        metadata = DocumentMetadata(
            title=title,
            source_path=str(file_path),
            file_type="pdf",
        )
        
        chunks = []
        current_section_path = []
        current_text_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block["type"] != 0: continue
                
                for line in block["lines"]:
                    text = " ".join(span["text"] for span in line["spans"]).strip()
                    if not text: continue
                    
                    max_font_size = max(span["size"] for span in line["spans"])
                    is_heading = max_font_size > 12
                    
                    if is_heading:
                        if current_text_parts:
                            chunks.append(self._make_chunk(current_text_parts, metadata.doc_id, current_section_path, page_num + 1))
                            current_text_parts = []
                        
                        level = 1 if max_font_size > 18 else 2 if max_font_size > 14 else 3
                        current_section_path = current_section_path[:level-1] + [text]
                    else:
                        current_text_parts.append(text)
                        
            if current_text_parts:
                chunks.append(self._make_chunk(current_text_parts, metadata.doc_id, current_section_path, page_num + 1))
                current_text_parts = []
                
        doc.close()
        return ParsedDocument(metadata=metadata, chunks=chunks)

    def _make_chunk(self, text_parts: list[str], doc_id: str, section_path: list[str], page: int) -> Chunk:
        return Chunk(
            text=" ".join(text_parts),
            doc_id=doc_id,
            title=section_path[0] if section_path else "Без названия",
            section_path=" > ".join(section_path) if section_path else "Общий раздел",
            page_number=page
        )