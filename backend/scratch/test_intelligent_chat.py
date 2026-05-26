from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services import private_chat_service
from app.services.private_chat_service import LOCAL_ENGINE_OFFLINE_CODE, answer_private_rfp_question, detect_chat_intent


RF_ID = 19
FAKE_CHUNKS = [
    {
        "chunk_id": 101,
        "chunk_order": 1,
        "section_title": "Metadata",
        "page_number": 1,
        "score": 0.82,
        "retrieval_type": "hybrid",
        "chunk_text": "Client: National Accounts Division.",
        "preview": "Client: National Accounts Division.",
    }
]


def main() -> None:
    init_db()
    rows: list[tuple[str, str, str, str]] = []

    def add(test: str, ok: bool, evidence: str, notes: str = "") -> None:
        rows.append((test, "PASS" if ok else "FAIL", evidence, notes))

    with SessionLocal() as db:
        rfp = db.get(RFPDocument, RF_ID)
        assert rfp is not None, "Test RFP not found."

        local_intent_cases = [
            ("hii", "greeting", "Private RFP Assistant"),
            ("Thanks", "thanks", "You're welcome"),
            ("is this using cloud?", "status", "private mode"),
            ("what is the weather?", "unsupported_general", "document"),
        ]

        with patch.object(private_chat_service, "search_chunks", side_effect=_explode_if_called), patch.object(
            private_chat_service, "chat_local", side_effect=_explode_if_called
        ):
            for text, expected_intent, expected_phrase in local_intent_cases:
                result = answer_private_rfp_question(db, RF_ID, text)
                add(
                    text,
                    result["intent"] == expected_intent
                    and result["provider"] == "local"
                    and result["external_api_used"] is False
                    and result["source_chunks"] == []
                    and expected_phrase.lower() in result["answer"].lower(),
                    f"intent={result['intent']} provider={result['provider']} chunks={len(result['source_chunks'])} answer={result['answer']}",
                    "",
                )

        intent = detect_chat_intent("what is my client name")
        add("intent client", intent["intent"] == "rfp_question", str(intent), "")
        intent = detect_chat_intent("What is the deadline?")
        add("intent deadline", intent["intent"] == "rfp_question", str(intent), "")

        result = _answer_with_stubs(db, "what is my client name")
        offline_or_online_ok = result["intent"] == "rfp_question" and result["provider"] in {"local", "local_ollama"}
        if result["provider"] == "local":
            offline_or_online_ok = offline_or_online_ok and result["code"] == LOCAL_ENGINE_OFFLINE_CODE and result["source_chunks"] == []
        add(
            "what is my client name",
            offline_or_online_ok,
            f"provider={result['provider']} intent={result['intent']} code={result.get('code')} chunks={len(result['source_chunks'])}",
            "",
        )

        result = _answer_with_stubs(db, "What is the deadline?")
        add(
            "What is the deadline?",
            result["intent"] == "rfp_question" and result["provider"] in {"local", "local_ollama"},
            f"provider={result['provider']} intent={result['intent']} chunks={len(result['source_chunks'])}",
            "",
        )

        offline = _simulate_offline_response(db)
        add(
            "offline response",
            offline["provider"] == "local"
            and offline["code"] == LOCAL_ENGINE_OFFLINE_CODE
            and offline["intent"] == "rfp_question"
            and offline["source_chunks"] == []
            and "local ai engine is currently offline" in offline["answer"].lower(),
            f"provider={offline['provider']} code={offline.get('code')} answer={offline['answer']}",
            "",
        )

    print("Test | Status | Evidence | Notes")
    print("---|---|---|---")
    for row in rows:
        print(" | ".join(str(col).replace("\n", " ") for col in row))

    if any(row[1] == "FAIL" for row in rows):
        raise SystemExit(1)


def _simulate_offline_response(db):
    original_health = private_chat_service.get_ollama_health
    original_search = private_chat_service.search_chunks
    original_chat = private_chat_service.chat_local
    private_chat_service.get_ollama_health = lambda: {  # type: ignore[assignment]
        "available": False,
        "chat_model_available": False,
        "embedding_model_available": True,
        "message": "Ollama is offline. Start Ollama and retry.",
    }
    private_chat_service.search_chunks = _explode_if_called  # type: ignore[assignment]
    private_chat_service.chat_local = _explode_if_called  # type: ignore[assignment]
    try:
        with SessionLocal() as offline_db:
            return answer_private_rfp_question(offline_db, RF_ID, "What are the risks?")
    finally:
        private_chat_service.get_ollama_health = original_health  # type: ignore[assignment]
        private_chat_service.search_chunks = original_search  # type: ignore[assignment]
        private_chat_service.chat_local = original_chat  # type: ignore[assignment]


def _answer_with_stubs(db, question: str):
    original_search = private_chat_service.search_chunks
    original_chat = private_chat_service.chat_local
    private_chat_service.search_chunks = lambda *args, **kwargs: FAKE_CHUNKS  # type: ignore[assignment]
    private_chat_service.chat_local = lambda *args, **kwargs: {  # type: ignore[assignment]
        "ok": True,
        "text": "Stub answer for regression coverage.",
        "provider": "local_ollama",
        "model_used": "llama3.2:3b",
        "elapsed_seconds": 0.01,
    }
    try:
        with SessionLocal() as stub_db:
            return answer_private_rfp_question(stub_db, RF_ID, question)
    finally:
        private_chat_service.search_chunks = original_search  # type: ignore[assignment]
        private_chat_service.chat_local = original_chat  # type: ignore[assignment]


def _explode_if_called(*_args, **_kwargs):
    raise AssertionError("local intents should not call retrieval or chat_local.")


if __name__ == "__main__":
    main()
