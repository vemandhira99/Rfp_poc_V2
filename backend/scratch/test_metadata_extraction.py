from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.metadata_extraction_service import extract_probable_metadata


def main() -> None:
    rows: list[tuple[str, str, str, str]] = []

    def add(test: str, ok: bool, evidence: str, notes: str = "") -> None:
        rows.append((test, "PASS" if ok else "FAIL", evidence, notes))

    toc_deadline = extract_probable_metadata("Technical Bid Evaluation .................. 44", "sample.pdf")
    add("toc deadline negative", toc_deadline["probable_deadline"] is None, str(toc_deadline), "")

    toc_submission = extract_probable_metadata("Form 1: Letter of Technical Proposal Submission Form .......... 90", "sample.pdf")
    add("toc submission negative", toc_submission["probable_submission_date"] is None, str(toc_submission), "")

    mixed_text = """
    TABLE OF CONTENTS
    Technical Bid Evaluation .................. 44
    Form 1: Letter of Technical Proposal Submission Form .......... 90
    Important Dates
    Last date of submission: 08.09.2025 (15:00 Hrs IST)
    Proposal submission due date - 25 September 2025
    """
    mixed = extract_probable_metadata(mixed_text, "sample.pdf")
    add("deadline actual date", "08.09.2025" in str(mixed["probable_deadline"] or ""), str(mixed), "")
    add("submission actual date", "08.09.2025" in str(mixed["probable_submission_date"] or "") or "25 September 2025" in str(mixed["probable_submission_date"] or ""), str(mixed), "")
    add("toc not selected", "Technical Bid Evaluation" not in str(mixed.get("probable_deadline")) and "Form 1" not in str(mixed.get("probable_submission_date")), str(mixed), "")
    add("confidence present", float(mixed.get("metadata_confidence") or 0) > 0, str(mixed), "")

    print("Test | Status | Evidence | Notes")
    print("---|---|---|---")
    for row in rows:
        print(" | ".join(str(col).replace("\n", " ") for col in row))

    if any(row[1] == "FAIL" for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
