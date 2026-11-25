from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    doc_id: str
    title: str
    file_type: str
    chunks: int
    was_created: bool
    took_ms: float


class DocumentListItem(BaseModel):
    doc_id: str
    title: str
    file_type: str | None
    file_size: str | None
    content_hash: str
    chunks: int
    created_at: datetime
    source_path: str | None
    stored: bool


class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ReindexResponse(BaseModel):
    doc_id: str
    title: str
    chunks: int
    took_ms: float