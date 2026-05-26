import json
import logging
import re
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.rfp import ChatMessage, RFPDocument
from app.services.local_ai_runtime_service import (
    CHAT_BUSY_MESSAGE,
    GENERATION_BUSY_MESSAGE,
    LOCAL_ENGINE_BUSY,
    LOCAL_ENGINE_OFFLINE,
    LOCAL_ENGINE_TIMEOUT,
    LOCAL_MODEL_MISSING,
    OFFLINE_MESSAGE,
    claim_operation,
    current_operation_kind,
)
from app.services.local_llm_service import chat_local
from app.services.ollama_health_service import get_ollama_health
from app.services.retrieval_service import search_chunks
from app.services.usage_service import log_local_usage
from app.utils.text_utils import safe_preview


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a private local RFP assistant. Use only the provided RFP excerpts. "
    "Do not invent facts. If the answer is not present in the excerpts, say the uploaded RFP does not contain enough information. "
    "Keep the answer clear, professional, and useful for a project manager or solution architect."
)

GREETING_RESPONSE = (
    "Hi, I'm your Private RFP Assistant. I can help you understand this RFP, identify requirements, "
    "summarize risks, explain deadlines, and generate a private draft - all locally."
)
THANKS_RESPONSE = (
    "You're welcome. You can ask me about scope, eligibility, requirements, risks, deadlines, "
    "compliance, or proposal strategy for this RFP."
)
HELP_RESPONSE = (
    "I can help with:\n"
    "1. Summarizing this RFP\n"
    "2. Finding scope and requirements\n"
    "3. Explaining deadlines\n"
    "4. Identifying risks\n"
    "5. Checking compliance themes\n"
    "6. Supporting private draft generation\n"
    "Ask something like: 'What are the key requirements?' or 'What are the main risks?'"
)
STATUS_RESPONSE = (
    "This workspace is running in private mode. Uploaded documents, embeddings, retrieval, chat, "
    "draft generation, and DOCX export stay local. external_api_used=false."
)
UNSUPPORTED_RESPONSE = (
    "I'm focused on this uploaded RFP. Please ask a question about the document, requirements, risks, "
    "deadlines, compliance, or proposal drafting."
)
NO_RELEVANT_CONTENT_RESPONSE = (
    "I could not find enough relevant content in the uploaded RFP to answer this confidently."
)
OFFLINE_RFP_RESPONSE = OFFLINE_MESSAGE
LOCAL_ENGINE_OFFLINE_CODE = LOCAL_ENGINE_OFFLINE
LOCAL_ENGINE_TIMEOUT_CODE = LOCAL_ENGINE_TIMEOUT
LOCAL_ENGINE_BUSY_CODE = LOCAL_ENGINE_BUSY
LOCAL_MODEL_MISSING_CODE = LOCAL_MODEL_MISSING
LOCAL_ENGINE_ERROR_CODE = "LOCAL_ENGINE_ERROR"
MAX_CHAT_CHUNK_CHARS = 900

GREETING_PHRASES = {
    "hi",
    "hii",
    "hiii",
    "hello",
    "hey",
    "heyy",
    "hey yo",
    "good morning",
    "good afternoon",
    "good evening",
}

THANKS_PHRASES = {
    "thanks",
    "thank you",
    "thankyou",
    "thx",
    "okay thanks",
    "ok thanks",
    "ok thx",
    "got it",
    "got it thanks",
    "nice thanks",
    "nice",
}

HELP_PHRASES = {
    "help",
    "what can you do",
    "how can you help",
    "what should i ask",
    "what can i ask",
}

STATUS_PHRASES = {
    "is this local",
    "are you using cloud",
    "is external api used",
    "where is my data going",
    "is this private",
    "private mode",
    "local only",
    "is this using cloud",
}

UNRELATED_KEYWORDS = {
    "weather",
    "movie",
    "film",
    "music",
    "recipe",
    "sports",
    "sport",
    "stock",
    "finance",
    "news",
    "joke",
    "game",
    "travel",
    "restaurant",
    "horoscope",
    "shopping",
    "vacation",
    "birthday",
}

RFP_KEYWORDS = {
    "requirements",
    "requirement",
    "scope",
    "deadline",
    "deadlines",
    "client",
    "risk",
    "risks",
    "compliance",
    "eligibility",
    "penalty",
    "sla",
    "implementation",
    "technical",
    "architecture",
    "summary",
    "proposal",
    "section",
    "clause",
    "payment",
    "deliverables",
    "submission",
    "bid",
    "timeline",
    "evaluation",
    "scoring",
    "security",
    "local",
    "private",
    "draft",
    "response",
    "rfp",
    "workspace",
    "deadline",
    "client",
    "requirements",
    "scope",
    "risk",
    "compliance",
    "proposal",
    "implementation",
    "sla",
    "payment",
    "eligibility",
    "bid",
    "submission",
}


def detect_chat_intent(question: str) -> dict[str, str]:
    normalized = _normalize(question)
    if not normalized:
        return _local_intent("unsupported_general", UNSUPPORTED_RESPONSE)

    if _matches_greeting(normalized):
        return _local_intent("greeting", GREETING_RESPONSE)
    if _matches_thanks(normalized):
        return _local_intent("thanks", THANKS_RESPONSE)
    if _matches_help(normalized):
        return _local_intent("help", HELP_RESPONSE)
    if _matches_status(normalized):
        return _local_intent("status", STATUS_RESPONSE)
    if any(keyword in normalized for keyword in RFP_KEYWORDS) or "what is this about" in normalized or "tell me about this" in normalized:
        return {"intent": "rfp_question", "provider": "local_ollama", "answer": "", "retrieval_mode": "hybrid"}
    if any(keyword in normalized for keyword in UNRELATED_KEYWORDS):
        return _local_intent("unsupported_general", UNSUPPORTED_RESPONSE)
    if any(token in normalized for token in {"who are you", "how are you", "your name", "what do you do"}):
        return _local_intent("unsupported_general", UNSUPPORTED_RESPONSE)
    return {"intent": "rfp_question", "provider": "local_ollama", "answer": "", "retrieval_mode": "hybrid"}


def answer_private_rfp_question(db: Session, rfp_id: int, question: str) -> dict:
    rfp = db.get(RFPDocument, rfp_id)
    if rfp is None:
        raise ValueError("RFP document not found.")

    clean_question = question.strip()
    intent_data = detect_chat_intent(clean_question)
    intent = intent_data["intent"]
    provider = intent_data["provider"]
    retrieval_mode = intent_data["retrieval_mode"]

    metadata_answer = _answer_from_metadata(rfp, clean_question)
    if metadata_answer is not None:
        answer, metadata_field = metadata_answer
        _save_chat_messages(db, rfp_id, clean_question, answer, "local_metadata", None, [])
        log_local_usage(
            db,
            operation_type="chat_rfp_metadata",
            model_used=None,
            prompt_text=clean_question,
            response_text=answer,
            rfp_id=rfp_id,
            elapsed_seconds=0.0,
            retrieval_chunks_used=0,
            external_api_used=False,
        )
        return _build_response(rfp_id, intent, answer, "local_metadata", None, "metadata", [], code=metadata_field)

    if intent in {"greeting", "thanks", "help", "status", "unsupported_general"}:
        answer = intent_data["answer"]
        _save_chat_messages(db, rfp_id, clean_question, answer, provider, None, [])
        log_local_usage(
            db,
            operation_type="chat_local_intent",
            model_used=None,
            prompt_text=clean_question,
            response_text=answer,
            rfp_id=rfp_id,
            elapsed_seconds=0.0,
            retrieval_chunks_used=0,
            external_api_used=False,
        )
        return _build_response(rfp_id, intent, answer, provider, None, retrieval_mode, [], code=None)

    health = get_ollama_health()
    if not health.get("available"):
        answer = OFFLINE_RFP_RESPONSE
        _save_chat_messages(db, rfp_id, clean_question, answer, "local", None, [])
        log_local_usage(
            db,
            operation_type="chat_rfp_question",
            model_used=None,
            prompt_text=clean_question,
            response_text=answer,
            rfp_id=rfp_id,
            elapsed_seconds=0.0,
            retrieval_chunks_used=0,
            external_api_used=False,
        )
        return _build_response(rfp_id, intent, answer, "local", None, "unavailable", [], code=LOCAL_ENGINE_OFFLINE_CODE)
    if not health.get("chat_model_available"):
        answer = health.get("message") or "A required local model is missing."
        _save_chat_messages(db, rfp_id, clean_question, answer, "local", None, [])
        log_local_usage(
            db,
            operation_type="chat_rfp_question",
            model_used=None,
            prompt_text=clean_question,
            response_text=answer,
            rfp_id=rfp_id,
            elapsed_seconds=0.0,
            retrieval_chunks_used=0,
            external_api_used=False,
        )
        return _build_response(rfp_id, intent, answer, "local", None, "unavailable", [], code=LOCAL_MODEL_MISSING_CODE)

    with claim_operation("chat", wait_seconds=2.0) as claim:
        if claim is None:
            busy_message = GENERATION_BUSY_MESSAGE if current_operation_kind() == "generation" else CHAT_BUSY_MESSAGE
            code = LOCAL_ENGINE_BUSY_CODE
            _save_chat_messages(db, rfp_id, clean_question, busy_message, "local", None, [])
            log_local_usage(
                db,
                operation_type="chat_rfp_question",
                model_used=None,
                prompt_text=clean_question,
                response_text=busy_message,
                rfp_id=rfp_id,
                elapsed_seconds=0.0,
                retrieval_chunks_used=0,
                external_api_used=False,
            )
            retrieval_mode = "unavailable" if current_operation_kind() == "generation" else "local"
            return _build_response(rfp_id, intent, busy_message, "local", None, retrieval_mode, [], code=code)

        source_chunks = search_chunks(db, rfp_id, clean_question, top_k=3, mode="hybrid")
        useful_chunks = [chunk for chunk in source_chunks if float(chunk["score"]) > 0]
        if not useful_chunks:
            answer = NO_RELEVANT_CONTENT_RESPONSE
            _save_chat_messages(db, rfp_id, clean_question, answer, "local", None, [])
            log_local_usage(
                db,
                operation_type="chat_rfp_question",
                model_used=None,
                prompt_text=clean_question,
                response_text=answer,
                rfp_id=rfp_id,
                elapsed_seconds=0.0,
                retrieval_chunks_used=0,
                external_api_used=False,
            )
            return _build_response(rfp_id, intent, answer, "local", None, "local", [], code=None)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(clean_question, useful_chunks)},
        ]
        result = chat_local(messages, temperature=0.2, timeout=180, runtime_token=claim.token if claim.owns_lock else None)
        if not result.get("ok"):
            code = str(result.get("code") or LOCAL_ENGINE_ERROR_CODE)
            answer, retrieval_mode = _friendly_runtime_failure_message(code, result.get("error") or result.get("message"))
            logger.warning("local_ollama chat failed after health check: code=%s error=%s", code, result.get("error") or "unknown error")
            _save_chat_messages(db, rfp_id, clean_question, answer, "local", None, [])
            log_local_usage(
                db,
                operation_type="chat_rfp_question",
                model_used=None,
                prompt_text=_build_user_prompt(clean_question, useful_chunks),
                response_text=answer,
                rfp_id=rfp_id,
                elapsed_seconds=float(result.get("elapsed_seconds") or 0),
                retrieval_chunks_used=0,
                external_api_used=False,
            )
            return _build_response(rfp_id, intent, answer, "local", None, retrieval_mode, [], code=code)

        answer = result.get("text") or NO_RELEVANT_CONTENT_RESPONSE
        model_used = result.get("model_used", settings.OLLAMA_CHAT_MODEL)
        _save_chat_messages(db, rfp_id, clean_question, str(answer), "local_ollama", model_used, useful_chunks)
        log_local_usage(
            db,
            operation_type="chat_rfp_question",
            model_used=model_used,
            prompt_text=_build_user_prompt(clean_question, useful_chunks),
            response_text=str(answer),
            rfp_id=rfp_id,
            elapsed_seconds=float(result.get("elapsed_seconds") or 0),
            retrieval_chunks_used=len(useful_chunks),
            external_api_used=False,
        )
        return _build_response(rfp_id, intent, str(answer), "local_ollama", model_used, retrieval_mode, useful_chunks, code=None)


def _answer_from_metadata(rfp: RFPDocument, question: str) -> tuple[str, str] | None:
    normalized = _normalize(question)
    if not normalized:
        return None

    client_patterns = (
        "client name",
        "who is the client",
        "who is the client name",
        "name of the client",
        "what is the client name",
    )
    if any(pattern in normalized for pattern in client_patterns):
        return _format_metadata_answer("client", rfp.probable_client), "CLIENT_NAME"

    deadline_patterns = (
        "deadline",
        "due date",
        "submission date",
        "when is it due",
        "what is the deadline",
        "what is the due date",
    )
    if any(pattern in normalized for pattern in deadline_patterns):
        return _format_metadata_answer("deadline", rfp.probable_deadline or rfp.probable_submission_date), "DEADLINE"

    title_patterns = (
        "what is the title",
        "title of the rfp",
        "rfp title",
        "name of the rfp",
        "document title",
    )
    if any(pattern in normalized for pattern in title_patterns):
        return _format_metadata_answer("title", rfp.probable_title or rfp.title), "TITLE"

    return None


def _format_metadata_answer(field_name: str, value: str | None) -> str:
    if value:
        return f"The probable {field_name} is {value}."
    return f"I could not find a clear {field_name} in the uploaded RFP."


def _build_response(
    rfp_id: int,
    intent: str,
    answer: str,
    provider: str,
    model_used: str | None,
    retrieval_mode: str,
    source_chunks: list[dict],
    code: str | None = None,
) -> dict:
    return {
        "rfp_id": rfp_id,
        "answer": answer,
        "provider": provider,
        "model_used": model_used,
        "intent": intent,
        "retrieval_mode": retrieval_mode,
        "external_api_used": False,
        "source_chunks": source_chunks,
        "code": code,
    }


def _friendly_runtime_failure_message(code: str, fallback: str | None) -> tuple[str, str]:
    if code == LOCAL_ENGINE_BUSY_CODE:
        return (
            GENERATION_BUSY_MESSAGE if fallback and "draft generation" in fallback.lower() else CHAT_BUSY_MESSAGE,
            "unavailable",
        )
    if code == LOCAL_ENGINE_TIMEOUT_CODE:
        return ("The local AI engine took too long to respond. Try again in a moment.", "unavailable")
    if code == LOCAL_MODEL_MISSING_CODE:
        return (fallback or "A required local model is missing.", "unavailable")
    if code == LOCAL_ENGINE_OFFLINE_CODE:
        return (fallback or OFFLINE_RFP_RESPONSE, "unavailable")
    return ("The local AI engine encountered an error. Please try again in a moment.", "unavailable")


def _build_user_prompt(question: str, chunks: Sequence[dict]) -> str:
    excerpts = []
    for chunk in chunks:
        excerpt = _clip_chunk_text(str(chunk.get("chunk_text") or ""))
        section = f" | Section: {chunk['section_title']}" if chunk.get("section_title") else ""
        page = f" | Page: {chunk['page_number']}" if chunk.get("page_number") else ""
        excerpts.append(f"[Chunk {chunk['chunk_order']}{section}{page}]\n{excerpt}")
    excerpt_text = "\n\n".join(excerpts) if excerpts else "No relevant excerpts found."
    return (
        "You are a private local RFP assistant. Use only the provided RFP excerpts. "
        "Do not invent facts. If the answer is not present in the excerpts, say the uploaded RFP does not contain enough information. "
        "Keep the answer clear, professional, and useful for a project manager or solution architect. Keep it concise.\n\n"
        f"RFP excerpts:\n{excerpt_text}\n\nQuestion: {question}\n\n"
        "Answer only from the excerpts. Be concise and mention uncertainty when needed."
    )


def _clip_chunk_text(text: str) -> str:
    normalized = text.strip()
    if len(normalized) <= MAX_CHAT_CHUNK_CHARS:
        return normalized
    return safe_preview(normalized, MAX_CHAT_CHUNK_CHARS)


def _save_chat_messages(
    db: Session,
    rfp_id: int,
    question: str,
    answer: str,
    provider: str,
    model_used: str | None,
    source_chunks: list[dict],
) -> None:
    db.add(ChatMessage(rfp_id=rfp_id, role="user", message=question, provider="local"))
    db.add(
        ChatMessage(
            rfp_id=rfp_id,
            role="assistant",
            message=answer,
            provider=provider,
            model_used=model_used,
            source_chunks_json=json.dumps(source_chunks),
        )
    )
    db.commit()


def _normalize(question: str) -> str:
    text = question.replace("\r", "\n").replace("\n", " ").lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [_collapse_repeated_chars(token) for token in text.split(" ") if token]
    return " ".join(tokens).strip()


def _collapse_repeated_chars(token: str) -> str:
    return re.sub(r"([a-z])\1{2,}", r"\1\1", token)


def _matches_greeting(normalized: str) -> bool:
    if normalized in GREETING_PHRASES:
        return True
    return any(
        phrase in normalized
        for phrase in [
            "good morning",
            "good afternoon",
            "good evening",
            "hi there",
            "hello there",
            "hey there",
        ]
    )


def _matches_thanks(normalized: str) -> bool:
    if normalized in THANKS_PHRASES:
        return True
    return any(
        phrase in normalized
        for phrase in [
            "thanks a lot",
            "thank you",
            "thankyou",
            "thanks",
            "ok thanks",
            "okay thanks",
            "got it thanks",
            "nice thanks",
            "thx",
        ]
    )


def _matches_help(normalized: str) -> bool:
    if normalized in HELP_PHRASES:
        return True
    return any(phrase in normalized for phrase in HELP_PHRASES)


def _matches_status(normalized: str) -> bool:
    if normalized in STATUS_PHRASES:
        return True
    return any(phrase in normalized for phrase in STATUS_PHRASES) or "cloud" in normalized or "external api" in normalized


def _local_intent(intent: str, answer: str) -> dict[str, str]:
    return {"intent": intent, "provider": "local", "answer": answer, "retrieval_mode": "local"}
