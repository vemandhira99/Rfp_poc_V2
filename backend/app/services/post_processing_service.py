import re

from app.utils.text_utils import count_words, normalize_text


def clean_duplicate_headings(text: str, section_title: str) -> str:
    lines = text.splitlines()
    cleaned_lines = []
    normalized_title = _normalize_heading(section_title)
    for line in lines:
        if _normalize_heading(line) == normalized_title:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def remove_markdown_artifacts(text: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)
    return normalize_text(text)


def normalize_bullets(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        stripped = re.sub(r"^[*•]\s+", "- ", stripped)
        lines.append(stripped)
    return "\n".join(lines).strip()


def trim_overlong_text(text: str, max_words: int = 900) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip()


def clean_section_text(text: str, section_title: str, max_words: int = 900) -> str:
    cleaned = remove_markdown_artifacts(text)
    cleaned = normalize_bullets(cleaned)
    cleaned = clean_duplicate_headings(cleaned, section_title)
    cleaned = trim_overlong_text(cleaned, max_words=max_words)
    return cleaned.strip()


def _normalize_heading(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
