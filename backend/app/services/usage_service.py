import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.rfp import LocalUsageLog
from app.utils.text_utils import count_words


def estimate_tokens_from_words(words: int) -> int:
    return int(math.ceil(max(words, 0) * 1.33))


def log_local_usage(
    db: Session,
    *,
    operation_type: str,
    model_used: str | None,
    prompt_text: str = "",
    response_text: str = "",
    rfp_id: int | None = None,
    elapsed_seconds: float | None = None,
    retrieval_chunks_used: int = 0,
    external_api_used: bool = False,
) -> LocalUsageLog:
    prompt_words = count_words(prompt_text)
    response_words = count_words(response_text)
    entry = LocalUsageLog(
        rfp_id=rfp_id,
        operation_type=operation_type,
        model_used=model_used,
        prompt_word_count=prompt_words,
        response_word_count=response_words,
        estimated_prompt_tokens=estimate_tokens_from_words(prompt_words),
        estimated_response_tokens=estimate_tokens_from_words(response_words),
        estimated_total_tokens=estimate_tokens_from_words(prompt_words + response_words),
        elapsed_seconds=elapsed_seconds,
        retrieval_chunks_used=retrieval_chunks_used,
        external_api_used=external_api_used,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def usage_summary(db: Session) -> dict[str, Any]:
    rows = db.query(
        func.count(LocalUsageLog.id),
        func.coalesce(func.sum(LocalUsageLog.estimated_total_tokens), 0),
        func.coalesce(func.sum(LocalUsageLog.elapsed_seconds), 0),
    ).one()
    return {
        "total_calls": int(rows[0] or 0),
        "estimated_total_tokens": int(rows[1] or 0),
        "total_elapsed_seconds": float(rows[2] or 0),
        "external_ai_calls": int(
            db.query(func.count(LocalUsageLog.id)).filter(LocalUsageLog.external_api_used.is_(True)).scalar() or 0
        ),
        "local_ai_calls": int(
            db.query(func.count(LocalUsageLog.id)).filter(LocalUsageLog.external_api_used.is_(False)).scalar() or 0
        ),
        "local_only": True,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def usage_for_rfp(db: Session, rfp_id: int) -> dict[str, Any]:
    logs = db.query(LocalUsageLog).filter(LocalUsageLog.rfp_id == rfp_id).order_by(LocalUsageLog.created_at.desc()).all()
    total_tokens = sum(log.estimated_total_tokens for log in logs)
    total_time = sum(float(log.elapsed_seconds or 0) for log in logs)
    return {
        "rfp_id": rfp_id,
        "total_calls": len(logs),
        "estimated_total_tokens": total_tokens,
        "total_elapsed_seconds": total_time,
        "external_ai_calls": sum(1 for log in logs if log.external_api_used),
        "entries": [
            {
                "id": log.id,
                "operation_type": log.operation_type,
                "model_used": log.model_used,
                "prompt_word_count": log.prompt_word_count,
                "response_word_count": log.response_word_count,
                "estimated_prompt_tokens": log.estimated_prompt_tokens,
                "estimated_response_tokens": log.estimated_response_tokens,
                "estimated_total_tokens": log.estimated_total_tokens,
                "elapsed_seconds": log.elapsed_seconds,
                "retrieval_chunks_used": log.retrieval_chunks_used,
                "external_api_used": log.external_api_used,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }
