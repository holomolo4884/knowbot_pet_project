from pathlib import Path
from typing import List
from loguru import logger
import json

from .models import ParsedDocument
from .parsers.pdf_parser import PDFParser
from .parsers.docx_parser import DOCXParser
from .parsers.markdown_parser import MarkdownParser

class IngestionProcessor:
    def __init__(self):
        self.parsers = {
            '.pdf': PDFParser(),
            '.docx': DOCXParser(),
            '.md': MarkdownParser(),
            '.markdown': MarkdownParser()
        }

    def process_directory(self, directory: Path) -> List[ParsedDocument]:
        directory = Path(directory)
        if not directory.is_dir():
            raise ValueError(f"Directory not found: {directory}")

        results = []
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.parsers:
                try:
                    parser = self.parsers[file_path.suffix.lower()]
                    parsed_doc = parser.parse(file_path)
                    results.append(parsed_doc)
                except Exception as e:
                    logger.error(f"Failed to parse {file_path.name}: {e}")
                    
        return results

    def save_to_json(self, documents: List[ParsedDocument], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Преобразуем dataclass в dict для JSON
        def to_dict(obj):
            if hasattr(obj, '__dict__'):
                return {k: to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [to_dict(i) for i in obj]
            return obj

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(to_dict(documents), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(documents)} documents to {output_path}")