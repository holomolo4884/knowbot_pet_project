from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    title: str | None = None
    section_path: str | None = None
    page_number: int | None = None
    score: float = Field(..., description="Косинусное сходство, 0..1")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=50)
    doc_id: str | None = None
    file_type: str | None = None


class SearchResponse(BaseModel):
    query: str
    took_ms: float
    results: list[RetrievedChunk]