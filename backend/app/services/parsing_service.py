from pathlib import Path

import fitz
from docx import Document

from app.utils.text_utils import normalize_text, text_stats


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text_from_file(file_path: str) -> dict[str, int | str]:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Supported files are PDF, DOCX, and TXT.")

    if extension == ".pdf":
        text, page_count = _extract_pdf(path)
    elif extension == ".docx":
        text, page_count = _extract_docx(path)
    else:
        text, page_count = _extract_txt(path)

    normalized = normalize_text(text)
    stats = text_stats(normalized, page_count=page_count)
    return {"text": normalized, **stats}


def _extract_pdf(path: Path) -> tuple[str, int]:
    with fitz.open(path) as doc:
        pages = [page.get_text("text") for page in doc]
        return "\n\n".join(pages), doc.page_count


def _extract_docx(path: Path) -> tuple[str, int]:
    document = Document(path)
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n\n".join(parts), 1


def _extract_txt(path: Path) -> tuple[str, int]:
    return path.read_text(encoding="utf-8", errors="ignore"), 1
