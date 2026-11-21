from pydantic import BaseModel, Field


class Citation(BaseModel):
    index: int = Field(..., description="Номер [N] в тексте ответа")
    chunk_id: str
    doc_id: str
    title: str | None = None
    section_path: str | None = None
    page_number: int | None = None
    score: float


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    doc_id: str | None = None
    file_type: str | None = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    grounded: bool
    abstained: bool
    invalid_citation_markers: int = 0
    retrieval_ms: float
    generation_ms: float
    model: str