import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.local_embedding_service import check_embedding_model, embed_text


def main() -> None:
    status = check_embedding_model()
    print("Embedding model status:", status)
    if not status.get("available"):
        return

    vector = embed_text("This RFP includes scope, deadline, evaluation criteria, and submission requirements.")
    print("Vector length:", len(vector))
    print("Is float list:", isinstance(vector, list) and all(isinstance(value, float) for value in vector[:10]))


if __name__ == "__main__":
    main()
