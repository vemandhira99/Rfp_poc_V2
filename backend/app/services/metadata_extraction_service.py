from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DATE_PATTERNS = [
    r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b(?:\s*\(\d{1,2}:\d{2}\s*(?:Hrs|hrs|IST|ist)?\))?",
    r"\b\d{4}-\d{2}-\d{2}\b(?:\s*\(\d{1,2}:\d{2}\s*(?:Hrs|hrs|IST|ist)?\))?",
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b(?:\s*\(\d{1,2}:\d{2}\s*(?:Hrs|hrs|IST|ist)?\))?",
]

CLIENT_KEYWORDS = [
    "national accounts division",
    "ministry of statistics",
    "mospi",
    "ministry",
    "department",
    "authority",
    "government",
    "directorate",
    "issued by",
    "client",
    "purchaser",
    "tendering authority",
]

TITLE_HINTS = ["request for proposal", "rfp", "tender", "bid", "proposal", "invitation"]

DEADLINE_HINTS = [
    "last date of submission",
    "bid submission",
    "submission deadline",
    "proposal submission",
    "due date",
    "closing date",
    "important dates",
    "target date and time",
    "deadline",
    "last date",
    "submission",
    "technical bid",
    "opening of technical bids",
]

TOC_PATTERNS = [
    r"\.{3,}\s*\d+\s*$",
    r"^\s*form\s+\d+\s*:\s*.+?\.{3,}\s*\d+\s*$",
    r"\bpage\s*\d+\s*$",
]


@dataclass
class MetadataResult:
    probable_title: str | None
    probable_client: str | None
    probable_deadline: str | None
    probable_submission_date: str | None
    metadata_confidence: float
    metadata_reason: str
    metadata_source_snippet: str | None


def extract_probable_metadata(text: str, filename: str) -> dict[str, str | float | None]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = _extract_metadata(lines, filename)
    return {
        "probable_title": result.probable_title,
        "probable_client": result.probable_client,
        "probable_deadline": result.probable_deadline,
        "probable_submission_date": result.probable_submission_date,
        "metadata_confidence": round(result.metadata_confidence, 2),
        "metadata_reason": result.metadata_reason,
        "metadata_source_snippet": result.metadata_source_snippet,
    }


def _extract_metadata(lines: list[str], filename: str) -> MetadataResult:
    title = _extract_title(lines, filename)
    client = _extract_client(lines)
    deadline, deadline_snippet = _extract_date_with_context(lines, DEADLINE_HINTS)
    submission, submission_snippet = _extract_date_with_context(
        lines,
        ["last date of submission", "bid submission", "submission deadline", "proposal submission", "due date", "closing date", "important dates", "target date and time", "submission"],
    )

    confidence = 0.0
    reasons: list[str] = []
    source_snippets: list[str] = []
    if title:
        confidence += 0.25
        reasons.append("title detected from heading")
    if client:
        confidence += 0.35
        reasons.append("client detected from issuer line")
    if deadline:
        confidence += 0.25
        reasons.append("deadline detected near date keywords")
        if deadline_snippet:
            source_snippets.append(deadline_snippet)
    if submission:
        confidence += 0.15
        reasons.append("submission date detected near date keywords")
        if submission_snippet and submission_snippet not in source_snippets:
            source_snippets.append(submission_snippet)
    if not reasons:
        reasons.append("metadata fallback used; no strong signal found")

    if deadline and not submission:
        submission = deadline
        if deadline_snippet:
            source_snippets.append(deadline_snippet)

    return MetadataResult(
        probable_title=title,
        probable_client=client,
        probable_deadline=deadline,
        probable_submission_date=submission,
        metadata_confidence=min(confidence, 1.0),
        metadata_reason="; ".join(reasons),
        metadata_source_snippet=" | ".join(source_snippets) if source_snippets else None,
    )


def _extract_title(lines: list[str], filename: str) -> str | None:
    candidates: list[tuple[float, str]] = []
    for line in lines[:35]:
        if _is_toc_line(line):
            continue
        if not (8 <= len(line) <= 160):
            continue
        lower = line.lower()
        if "table of contents" in lower or lower == "contents":
            continue
        if any(hint in lower for hint in DEADLINE_HINTS) or _find_date_match(line):
            continue
        score = 0.0
        if _looks_title_like(line):
            score += 0.35
        if any(hint in lower for hint in TITLE_HINTS):
            score += 0.4
        if len(line.split()) <= 14:
            score += 0.1
        if line.isupper():
            score += 0.1
        if score > 0:
            candidates.append((score, line.strip(" :-")))
    if candidates:
        candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        return candidates[0][1]

    stem = re.sub(r"[_\-]+", " ", Path(filename).stem).strip()
    return stem[:120] if stem else None


def _extract_client(lines: list[str]) -> str | None:
    candidates: list[tuple[float, str]] = []
    for index, line in enumerate(lines[:200]):
        if _is_toc_line(line):
            continue
        lower = line.lower()
        if not any(keyword in lower for keyword in CLIENT_KEYWORDS):
            continue

        score = 0.25
        if lower.startswith(("client", "authority", "department", "ministry", "issued by", "purchaser", "tendering authority")):
            score += 0.25
        candidate = _clean_label_value(line)
        if len(candidate) < 4 and index + 1 < len(lines):
            candidate = f"{candidate} {lines[index + 1].strip()}".strip()
        candidates.append((score, candidate))

        for keyword in ("issued by", "tendering authority", "purchaser", "client", "authority"):
            if keyword in lower:
                extracted = _value_after_keyword(line, keyword)
                if extracted:
                    candidates.append((score + 0.1, extracted))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    best = candidates[0][1]
    return best if len(best) >= 3 else None


def _extract_date_with_context(lines: list[str], hints: list[str]) -> tuple[str | None, str | None]:
    candidates: list[tuple[float, str, str]] = []
    for index, line in enumerate(lines[:260]):
        if _is_toc_line(line):
            continue
        lower = line.lower()
        if not any(hint in lower for hint in hints):
            continue

        date = _find_date_match(line)
        if date:
            candidates.append((0.98, _normalize_spacing(line), _normalize_spacing(line)))
            continue

        for offset in range(1, 4):
            if index + offset >= len(lines):
                break
            neighbour = lines[index + offset].strip()
            if _is_toc_line(neighbour):
                continue
            neighbour_date = _find_date_match(neighbour)
            if neighbour_date:
                combined = f"{line} {neighbour}".strip()
                candidates.append((0.85 - (offset * 0.05), _normalize_spacing(combined), _normalize_spacing(combined)))
                break

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: (item[0], len(item[2])), reverse=True)
    best = candidates[0]
    return best[1], best[2]


def _find_date_match(text: str) -> str | None:
    matches: list[str] = []
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            matches.append(match.group(0).strip())
    if not matches:
        return None
    matches.sort(key=len, reverse=True)
    return matches[0]


def _is_toc_line(line: str) -> bool:
    text = line.strip()
    if not text:
        return True
    if sum(1 for char in text if char == ".") >= 5:
        return True
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in TOC_PATTERNS):
        return True
    if re.search(r"\b\w+\s+\d{2,4}\s*$", text) and not _find_date_match(text):
        return True
    return False


def _line_or_window(lines: list[str], index: int) -> str:
    window = [lines[index].strip()]
    for offset in range(1, 3):
        if index + offset < len(lines):
            neighbour = lines[index + offset].strip()
            if neighbour and not _is_toc_line(neighbour):
                window.append(neighbour)
    return " ".join(window)


def _value_after_keyword(line: str, keyword: str) -> str | None:
    match = re.search(rf"{re.escape(keyword)}\s*[:\-]\s*(.+)$", line, flags=re.IGNORECASE)
    if match:
        return _clean_label_value(match.group(1))
    match = re.search(rf"{re.escape(keyword)}\s+(.+)$", line, flags=re.IGNORECASE)
    if match:
        return _clean_label_value(match.group(1))
    return None


def _clean_label_value(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" :-")
    return cleaned[:160]


def _normalize_spacing(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _looks_title_like(line: str) -> bool:
    letters = sum(1 for char in line if char.isalpha())
    return letters >= 8 and (line == line.title() or line.isupper() or len(line.split()) <= 16)
