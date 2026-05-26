from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services import private_chat_service
from app.services.private_chat_service import answer_private_rfp_question


RF_ID = 19
FAKE_CHUNKS = [
    {
        "chunk_id": 1,
        "chunk_order": 1,
        "section_title": "Client and Schedule",
        "page_number": 1,
        "score": 1.0,
        "retrieval_type": "hybrid",
        "chunk_text": "Client: National Accounts Division. Deadline: 25.09.2025.",
        "preview": "Client: National Accounts Division. Deadline: 25.09.2025.",
    }
]


def main() -> None:
    init_db()
    rows: list[tuple[str, str, str, str]] = []

    def add(test: str, ok: bool, evidence: str, notes: str = "") -> None:
        rows.append((test, "PASS" if ok else "FAIL", evidence, notes))

    sequence = [
        ("hi", "greeting"),
        ("hii", "greeting"),
        ("Thanks", "thanks"),
        ("what is my client name", "rfp_question"),
        ("What is the deadline?", "rfp_question"),
        ("hi", "greeting"),
        ("what is my client name", "rfp_question"),
    ]

    with SessionLocal() as db:
        rfp = db.get(RFPDocument, RF_ID)
        assert rfp is not None, "Test RFP not found."

        original_search = private_chat_service.search_chunks
        original_chat = private_chat_service.chat_local
        original_health = private_chat_service.get_ollama_health
        private_chat_service.search_chunks = lambda *args, **kwargs: FAKE_CHUNKS  # type: ignore[assignment]
        private_chat_service.chat_local = lambda *args, **kwargs: {  # type: ignore[assignment]
            "ok": True,
            "text": "Stub answer for client/deadline.",
            "provider": "local_ollama",
            "model_used": "llama3.2:3b",
            "elapsed_seconds": 0.01,
        }
        private_chat_service.get_ollama_health = lambda: {  # type: ignore[assignment]
            "available": True,
            "chat_model_available": True,
            "embedding_model_available": True,
            "message": "ok",
        }
        try:
            for idx, (text, expected_intent) in enumerate(sequence, start=1):
                result = answer_private_rfp_question(db, RF_ID, text)
                if expected_intent == "rfp_question":
                    ok = (
                        result["intent"] == "rfp_question"
                        and result["provider"] == "local_ollama"
                        and len(result["source_chunks"]) > 0
                        and "Ollama is not running" not in result["answer"]
                    )
                elif expected_intent == "greeting":
                    ok = result["intent"] == "greeting" and result["provider"] == "local" and result["source_chunks"] == []
                else:
                    ok = result["intent"] == "thanks" and result["provider"] == "local" and result["source_chunks"] == []
                add(
                    f"{idx}. {text}",
                    ok,
                    f"intent={result['intent']} provider={result['provider']} answer={result['answer']} chunks={len(result['source_chunks'])}",
                    "",
                )

            replay = answer_private_rfp_question(db, RF_ID, "Thanks")
            add(
                "replay thanks",
                replay["intent"] == "thanks" and "welcome" in replay["answer"].lower() and replay["provider"] == "local",
                f"intent={replay['intent']} provider={replay['provider']} answer={replay['answer']}",
                "",
            )
        finally:
            private_chat_service.search_chunks = original_search  # type: ignore[assignment]
            private_chat_service.chat_local = original_chat  # type: ignore[assignment]
            private_chat_service.get_ollama_health = original_health  # type: ignore[assignment]

    print("Test | Status | Evidence | Notes")
    print("---|---|---|---")
    for row in rows:
        print(" | ".join(str(col).replace("\n", " ") for col in row))

    if any(row[1] == "FAIL" for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
