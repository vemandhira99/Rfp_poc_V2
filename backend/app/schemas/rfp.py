from datetime import datetime

from pydantic import Field
from pydantic import BaseModel


class RFPDocumentSummary(BaseModel):
    id: int
    title: str | None
    original_filename: str
    file_type: str
    file_size: int
    page_count: int
    word_count: int
    character_count: int
    line_count: int
    probable_title: str | None = None
    probable_client: str | None = None
    probable_deadline: str | None = None
    probable_submission_date: str | None = None
    metadata_confidence: float | None = None
    metadata_reason: str | None = None
    generation_job_id: int | None = None
    generation_status: str | None = None
    generation_current_section: str | None = None
    generation_progress_percent: int | None = None
    generation_updated_at: datetime | None = None
    generation_started_at: datetime | None = None
    metadata_source_snippet: str | None = None
    document_quality: str
    classification_reason: str | None
    status: str
    chunk_count: int = 0
    embedded_chunk_count: int = 0
    embedding_status: str = "not_started"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RFPDocumentDetail(RFPDocumentSummary):
    extracted_text: str | None
    extracted_text_preview: str | None = None


class RFPChunkResponse(BaseModel):
    id: int
    rfp_id: int
    chunk_order: int
    page_number: int | None
    section_title: str | None
    chunk_text: str
    word_count: int
    embedding_model: str | None = None
    embedding_status: str = "pending"
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadRFPResponse(BaseModel):
    rfp_id: int
    original_filename: str
    stored_filename: str
    file_type: str
    file_size: int
    page_count: int
    word_count: int
    character_count: int
    line_count: int
    extracted_text_preview: str | None = None
    probable_title: str | None = None
    probable_client: str | None = None
    probable_deadline: str | None = None
    probable_submission_date: str | None = None
    document_quality: str
    status: str
    reason: str
    chunk_count: int
    external_api_used: bool = False


class RFPDraftSectionResponse(BaseModel):
    id: int
    rfp_id: int
    section_order: int
    section_title: str
    section_content: str
    model_used: str | None
    provider: str
    retrieval_summary_json: str | None
    word_count: int
    quality_status: str
    validation_status: str = "valid"
    validation_issues: list[str] = Field(default_factory=list)
    has_infrastructure_error: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
