import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, init_db
from app.models.rfp import RFPDocument
from app.services.local_embedding_service import embed_chunks_for_rfp
from app.services.retrieval_service import search_chunks


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        rfp = db.query(RFPDocument).order_by(RFPDocument.created_at.desc()).first()
        if rfp is None:
            print("No RFP found. Upload an RFP first.")
            return

        print("Embedding latest RFP:", {"rfp_id": rfp.id, "filename": rfp.original_filename})
        print(embed_chunks_for_rfp(db, rfp.id))

        results = search_chunks(db, rfp.id, "deadline requirements scope", top_k=5, mode="hybrid")
        for result in results:
            print(
                {
                    "chunk_id": result["chunk_id"],
                    "chunk_order": result["chunk_order"],
                    "score": result["score"],
                    "retrieval_type": result["retrieval_type"],
                    "preview": result["preview"],
                }
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
