import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.local_llm_service import chat_local, check_ollama_health


def main() -> None:
    health = check_ollama_health()
    print("Ollama health:", health)
    if not health.get("ok"):
        return

    result = chat_local([{"role": "user", "content": "Say hello in one sentence"}])
    print("Chat result:", result)


if __name__ == "__main__":
    main()
