from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


class SourceChunk(BaseModel):
    chunk_id: int
    chunk_order: int
    section_title: str | None = None
    page_number: int | None = None
    score: float
    retrieval_type: str | None = None
    chunk_text: str
    preview: str


class ChatResponse(BaseModel):
    rfp_id: int
    answer: str
    provider: str
    model_used: str | None
    intent: str | None = None
    retrieval_mode: str = "lexical_fallback"
    external_api_used: bool
    source_chunks: list[SourceChunk]
    code: str | None = None


class ChatHistoryItem(BaseModel):
    role: str
    message: str
    provider: str | None = None
    model_used: str | None = None
    intent: str | None = None
    source_chunks_json: str | None = None
    created_at: str
