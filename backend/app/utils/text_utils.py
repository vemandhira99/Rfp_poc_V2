import re


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def text_stats(text: str, page_count: int = 0) -> dict[str, int]:
    normalized = normalize_text(text)
    return {
        "page_count": page_count,
        "word_count": count_words(normalized),
        "character_count": len(normalized),
        "line_count": len(normalized.splitlines()) if normalized else 0,
    }


def safe_preview(text: str, max_chars: int = 500) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
