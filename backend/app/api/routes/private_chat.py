from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rfp import ChatMessage
from app.schemas.chat import ChatHistoryItem, ChatRequest, ChatResponse
from app.services.audit_service import log_event
from app.services.ollama_health_service import get_ollama_health
from app.services.private_chat_service import answer_private_rfp_question

router = APIRouter(prefix="/private-rfp", tags=["private-chat"])


@router.get("/ollama/status")
def get_ollama_status() -> dict:
    health = get_ollama_health()
    return health


@router.post("/{rfp_id}/chat", response_model=ChatResponse)
def chat_with_rfp(rfp_id: int, payload: ChatRequest, db: Session = Depends(get_db)) -> dict:
    try:
        result = answer_private_rfp_question(db, rfp_id, payload.question)
        log_event(
            db,
            event_type="private_chat_question_asked",
            action="chat_with_rfp",
            rfp_id=rfp_id,
            source="frontend",
            details={
                "question_length": len(payload.question),
                "intent": result.get("intent"),
                "provider": result.get("provider"),
                "retrieval_mode": result.get("retrieval_mode"),
                "source_chunk_count": len(result.get("source_chunks", [])),
            },
            external_api_used=False,
        )
        log_event(
            db,
            event_type="private_chat",
            action=str(result.get("intent") or "rfp_question"),
            rfp_id=rfp_id,
            source="frontend",
            details={
                "intent": result.get("intent"),
                "provider": result.get("provider"),
                "retrieval_mode": result.get("retrieval_mode"),
                "source_chunk_count": len(result.get("source_chunks", [])),
            },
            external_api_used=False,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{rfp_id}/chat-history", response_model=list[ChatHistoryItem])
def get_chat_history(rfp_id: int, limit: int = 20, db: Session = Depends(get_db)) -> list[ChatHistoryItem]:
    safe_limit = min(max(limit, 1), 20)
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.rfp_id == rfp_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    rows.reverse()
    history: list[ChatHistoryItem] = []
    for row in rows:
        history.append(
            ChatHistoryItem(
                role=row.role,
                message=row.message,
                provider=row.provider,
                model_used=row.model_used,
                intent=None,
                source_chunks_json=row.source_chunks_json,
                created_at=row.created_at.isoformat(),
            )
        )
    return history
