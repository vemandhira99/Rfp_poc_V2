import json
import logging
import threading
import time

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.rfp import RFPChunk, RFPDocument, RFPDraftSection
from app.services.draft_quality_service import REQUIRED_SECTIONS
from app.services.audit_service import log_event
from app.services.job_service import complete_generation_job, create_generation_job, fail_generation_job, update_generation_job
from app.services.job_service import get_latest_generation_job, mark_stale_generation_job_if_needed
from app.services.local_embedding_service import embed_chunks_for_rfp
from app.services.local_llm_service import chat_local
from app.services.local_ai_runtime_service import CHAT_BUSY_MESSAGE, LOCAL_ENGINE_BUSY, claim_operation
from app.services.post_processing_service import clean_section_text
from app.services.retrieval_service import search_chunks
from app.services.draft_validation_service import is_error_like_content, section_contains_invalid_content
from app.services.usage_service import log_local_usage
from app.utils.text_utils import count_words

logger = logging.getLogger(__name__)


SECTION_QUERIES = {
    "Executive Summary": "project objective client scope business outcome submission purpose",
    "Understanding of RFP": "scope of work objectives requirements background",
    "Proposed Solution Approach": "solution approach system platform workflow automation modules",
    "Functional and Technical Coverage": "functional requirements technical requirements non functional requirements integrations",
    "Security and Compliance Approach": "security compliance audit access control encryption data protection",
    "Implementation Plan": "implementation timeline phases deliverables training deployment",
    "Risk and Mitigation": "risks penalties SLA dependencies constraints assumptions",
    "Conclusion and Next Steps": "submission next steps proposal conclusion implementation readiness",
}

ALLOWED_GENERATION_STATUSES = {"ready_for_private_chat", "draft_generated"}
MAX_DRAFT_CHUNK_CHARS = 1000


class GenerationAlreadyRunningError(Exception):
    def __init__(self, current_job: dict[str, object], message: str = "Draft generation is already running for this RFP.", code: str = "GENERATION_ALREADY_RUNNING") -> None:
        super().__init__(message)
        self.code = code
        self.current_job = current_job


class _GenerationHeartbeat:
    def __init__(self, job_id: int, rfp_id: int, interval_seconds: int = 25) -> None:
        self.job_id = job_id
        self.rfp_id = rfp_id
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._section_title: str | None = None
        self._current_step = 0
        self._total_steps = 8
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def poke(self, section_title: str, current_step: int, total_steps: int) -> None:
        self._section_title = section_title
        self._current_step = current_step
        self._total_steps = total_steps

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            section_title = self._section_title or "the first section"
            db = SessionLocal()
            try:
                update_generation_job(db, self.job_id, self._current_step, self._total_steps, f"Still generating {section_title} locally...")
            except Exception as exc:  # pragma: no cover - heartbeat should never fail the job
                logger.debug("generation heartbeat failed for rfp_id=%s job_id=%s: %s", self.rfp_id, self.job_id, exc)
            finally:
                db.close()


def _job_snapshot(job) -> dict[str, object]:
    return {
        "job_id": job.id,
        "status": job.status,
        "current_step": job.current_step,
        "total_steps": job.total_steps,
        "progress_percent": job.progress_percent,
        "current_section": job.current_section,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
    }


def generate_private_short_draft(db: Session, rfp_id: int, confirm_regenerate: bool = False) -> dict:
    rfp = db.get(RFPDocument, rfp_id)
    if rfp is None:
        raise ValueError("RFP document not found.")
    _validate_rfp_for_generation(rfp)

    chunk_count = db.query(RFPChunk).filter(RFPChunk.rfp_id == rfp_id).count()
    if chunk_count == 0:
        raise ValueError("No chunks are available for this RFP. Re-upload or reprocess the document.")
    running_job = get_latest_generation_job(db, rfp_id)
    if running_job is not None:
        running_job = mark_stale_generation_job_if_needed(db, running_job) or running_job
    if running_job and running_job.status in {"queued", "running"}:
        raise GenerationAlreadyRunningError(_job_snapshot(running_job))
    if running_job and running_job.status == "failed_stale" and not confirm_regenerate:
        raise GenerationAlreadyRunningError(_job_snapshot(running_job), message="Draft generation is stale. Confirm regenerate before retrying.", code="GENERATION_STALE_REQUIRES_CONFIRMATION")

    existing_sections = db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp_id).order_by(RFPDraftSection.section_order).all()
    resume_mode = False
    if existing_sections:
        if confirm_regenerate:
            db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp_id).delete()
            db.commit()
            existing_sections = []
        else:
            latest_job = running_job
            if latest_job and latest_job.status == "failed_partial":
                resume_mode = True
            else:
                raise ValueError("Draft already exists. Pass confirm_regenerate=true before overwriting existing draft sections.")
    else:
        resume_mode = False

    with claim_operation("generation", wait_seconds=5.0) as claim:
        if claim is None:
            raise GenerationAlreadyRunningError({}, message=CHAT_BUSY_MESSAGE, code=LOCAL_ENGINE_BUSY)

        job = create_generation_job(db, rfp_id)
        job.model_used = settings.OLLAMA_CHAT_MODEL
        db.commit()
        log_event(db, "private_draft_generation_started", "generate_private_short_draft", rfp_id=rfp_id, entity_type="GenerationJob", entity_id=job.id, details={"total_steps": len(REQUIRED_SECTIONS), "resume_mode": resume_mode})

        heartbeat = _GenerationHeartbeat(job.id, rfp_id)
        heartbeat.start()
        try:
            _try_embed_chunks(db, rfp_id)

            generated = 0
            total_steps = len(REQUIRED_SECTIONS)
            existing_titles = {section.section_title for section in existing_sections}
            planned_sections = [section for section in REQUIRED_SECTIONS if section not in existing_titles]
            if not planned_sections:
                planned_sections = list(REQUIRED_SECTIONS)
            for section_title in planned_sections:
                section_order = REQUIRED_SECTIONS.index(section_title) + 1
                update_generation_job(db, job.id, section_order - 1, total_steps, section_title)
                heartbeat.poke(section_title, section_order - 1, total_steps)
                retrieved_chunks = search_chunks(db, rfp_id, SECTION_QUERIES[section_title], top_k=3, mode="hybrid")
                prompt = _build_section_prompt(section_title, retrieved_chunks)
                result = chat_local(
                    [
                        {"role": "system", "content": "You generate concise private local RFP response drafts using only retrieved excerpts."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    timeout=240,
                    runtime_token=claim.token if claim.owns_lock else None,
                )
                if not result.get("ok"):
                    error_message = str(result.get("error") or result.get("message") or "Draft generation failed.")
                    generated = _handle_generation_failure(db, job.id, generated, len(existing_sections), total_steps, error_message)
                    raise ValueError(error_message)

                raw_content = result.get("text") or ""
                cleaned = clean_section_text(str(raw_content), section_title, max_words=900)
                if section_contains_invalid_content(cleaned) or is_error_like_content(cleaned):
                    error_message = f"Section {section_title} contains invalid infrastructure text."
                    generated = _handle_generation_failure(db, job.id, generated, len(existing_sections), total_steps, error_message)
                    raise ValueError(error_message)

                db.add(
                    RFPDraftSection(
                        rfp_id=rfp_id,
                        section_order=section_order,
                        section_title=section_title,
                        section_content=cleaned,
                        model_used=result.get("model_used", settings.OLLAMA_CHAT_MODEL),
                        provider=result.get("provider", "local_ollama"),
                        retrieval_summary_json=json.dumps(_retrieval_summary(retrieved_chunks)),
                        word_count=count_words(cleaned),
                        quality_status="pending",
                    )
                )
                db.commit()
                generated += 1
                log_local_usage(
                    db,
                    operation_type="generation_section",
                    model_used=result.get("model_used", settings.OLLAMA_CHAT_MODEL),
                    prompt_text=prompt,
                    response_text=str(cleaned),
                    rfp_id=rfp_id,
                    elapsed_seconds=float(result.get("elapsed_seconds") or 0),
                    retrieval_chunks_used=len(retrieved_chunks),
                    external_api_used=False,
                )
                update_generation_job(db, job.id, section_order, total_steps, section_title)
                heartbeat.poke(section_title, section_order, total_steps)
                time.sleep(0.5)

            completed_sections = len(existing_sections) + generated
            if completed_sections == total_steps:
                rfp.status = "draft_generated"
                db.commit()
            complete_generation_job(db, job.id)
            log_event(db, "private_draft_generation_completed", "generate_private_short_draft", rfp_id=rfp_id, entity_type="GenerationJob", entity_id=job.id, details={"sections_generated": generated})
        except Exception as exc:
            current_job = db.get(job.__class__, job.id) if job is not None else None
            if current_job is not None and current_job.status not in {"failed", "failed_partial", "completed"}:
                fail_generation_job(db, job.id, str(exc))
            log_event(db, "private_draft_generation_failed", "generate_private_short_draft", rfp_id=rfp_id, entity_type="GenerationJob", entity_id=job.id, details={"error": str(exc)})
            raise
        finally:
            heartbeat.stop()

        completed_sections = len(existing_sections) + generated
        return {
            "rfp_id": rfp_id,
            "status": "completed" if completed_sections == total_steps else "failed_partial",
            "sections_generated": generated,
            "provider": "local_ollama",
            "external_api_used": False,
            "job_id": job.id,
        }


def _validate_rfp_for_generation(rfp: RFPDocument) -> None:
    if rfp.status == "needs_more_detail":
        raise ValueError("This document has insufficient detail and cannot support draft generation.")
    if rfp.status == "extraction_needs_review":
        raise ValueError("This document may be scanned or image-based. Review extraction before draft generation.")
    if rfp.status not in ALLOWED_GENERATION_STATUSES:
        raise ValueError(f"Document status '{rfp.status}' is not ready for private draft generation.")


def _try_embed_chunks(db: Session, rfp_id: int) -> None:
    embed_chunks_for_rfp(db, rfp_id)


def _build_section_prompt(section_title: str, chunks: list[dict]) -> str:
    excerpts = []
    for chunk in chunks:
        excerpts.append(f"[Chunk {chunk['chunk_order']}]\n{_clip_chunk_text(str(chunk.get('chunk_text') or ''))}")
    excerpt_text = "\n\n".join(excerpts) if excerpts else "No relevant excerpts found."
    return f"""You are generating a private local RFP response draft.
Use only the provided RFP excerpts.
Do not invent facts.
If information is missing, say "To be validated by the proposal team."
Do not include section number or section title in the content.
Do not use markdown tables.
Use professional tender-style language.
Keep the section concise.
Avoid repetition.
Limit the section to about 500-700 words.
Output plain text paragraphs and bullet points only.

Section to draft: {section_title}

Retrieved RFP excerpts:
{excerpt_text}
"""


def _clip_chunk_text(text: str) -> str:
    normalized = text.strip()
    if len(normalized) <= MAX_DRAFT_CHUNK_CHARS:
        return normalized
    return normalized[: MAX_DRAFT_CHUNK_CHARS - 3].rstrip() + "..."


def _retrieval_summary(chunks: list[dict]) -> list[dict]:
    return [
        {
            "chunk_id": chunk.get("chunk_id"),
            "chunk_order": chunk.get("chunk_order"),
            "score": chunk.get("score"),
            "retrieval_type": chunk.get("retrieval_type"),
        }
        for chunk in chunks
    ]


def _handle_generation_failure(db: Session, job_id: int, generated: int, existing_section_count: int, total_steps: int, error_message: str) -> int:
    status = "failed_partial" if generated > 0 or existing_section_count > 0 else "failed"
    fail_generation_job(db, job_id, error_message)
    completed_sections = generated + existing_section_count
    job = update_generation_job(db, job_id, completed_sections, total_steps, "Failed", status=status)
    if job is not None:
        job.error_message = error_message
        job.status = status
        db.commit()
    return generated
