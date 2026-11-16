from dataclasses import dataclass, field
from uuid import uuid4

@dataclass
class DocumentMetadata:
    doc_id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    source_path: str = ""
    file_type: str = ""

@dataclass
class Chunk:
    text: str
    doc_id: str
    title: str
    section_path: str
    page_number: int | None = None  # Для Markdown может быть None
    chunk_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("Chunk text cannot be empty")

@dataclass
class ParsedDocument:
    metadata: DocumentMetadata
    chunks: list[Chunk] = field(default_factory=list)