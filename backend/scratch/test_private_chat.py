import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services.private_chat_service import answer_private_rfp_question


def main() -> None:
    db = SessionLocal()
    try:
        result = answer_private_rfp_question(db, rfp_id=1, question="What is this RFP about?")
        print("Answer:", result["answer"])
        print("Source chunks:", result["source_chunks"])
    finally:
        db.close()


if __name__ == "__main__":
    main()
