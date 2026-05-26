from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RFPDocument(Base):
    __tablename__ = "rfp_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    character_count: Mapped[int] = mapped_column(Integer, default=0)
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_quality: Mapped[str] = mapped_column(String, default="unknown")
    classification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    probable_title: Mapped[str | None] = mapped_column(String, nullable=True)
    probable_client: Mapped[str | None] = mapped_column(String, nullable=True)
    probable_deadline: Mapped[str | None] = mapped_column(String, nullable=True)
    probable_submission_date: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks: Mapped[list["RFPChunk"]] = relationship(
        back_populates="rfp", cascade="all, delete-orphan", order_by="RFPChunk.chunk_order"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="rfp", cascade="all, delete-orphan")
    draft_sections: Mapped[list["RFPDraftSection"]] = relationship(
        back_populates="rfp", cascade="all, delete-orphan", order_by="RFPDraftSection.section_order"
    )
    draft_exports: Mapped[list["RFPDraftExport"]] = relationship(back_populates="rfp", cascade="all, delete-orphan")


class RFPChunk(Base):
    __tablename__ = "rfp_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rfp_id: Mapped[int] = mapped_column(ForeignKey("rfp_documents.id"), index=True)
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding_status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rfp: Mapped[RFPDocument] = relationship(back_populates="chunks")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rfp_id: Mapped[int] = mapped_column(ForeignKey("rfp_documents.id"), index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String, default="local")
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    source_chunks_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rfp: Mapped[RFPDocument] = relationship(back_populates="messages")


class RFPDraftSection(Base):
    __tablename__ = "rfp_draft_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rfp_id: Mapped[int] = mapped_column(ForeignKey("rfp_documents.id"), index=True)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str] = mapped_column(String, nullable=False)
    section_content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str] = mapped_column(String, default="local_ollama")
    retrieval_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rfp: Mapped[RFPDocument] = relationship(back_populates="draft_sections")


class RFPDraftExport(Base):
    __tablename__ = "rfp_draft_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rfp_id: Mapped[int] = mapped_column(ForeignKey("rfp_documents.id"), index=True)
    export_type: Mapped[str] = mapped_column(String, default="private_short_draft")
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    page_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rfp: Mapped[RFPDocument] = relationship(back_populates="draft_exports")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rfp_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, default="local_user")
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_api_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rfp_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String, default="private_short_draft")
    status: Mapped[str] = mapped_column(String, default="queued")
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=8)
    current_section: Mapped[str | None] = mapped_column(String, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    average_seconds_per_section: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_total_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_remaining_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_api_used: Mapped[bool] = mapped_column(Boolean, default=False)


class LocalUsageLog(Base):
    __tablename__ = "local_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rfp_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    operation_type: Mapped[str] = mapped_column(String, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_word_count: Mapped[int] = mapped_column(Integer, default=0)
    response_word_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_response_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_chunks_used: Mapped[int] = mapped_column(Integer, default=0)
    external_api_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
