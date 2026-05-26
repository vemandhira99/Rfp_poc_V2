import re

from sqlalchemy.orm import Session

from app.models.rfp import RFPDraftSection
from app.services.draft_validation_service import section_contains_invalid_content
from app.utils.text_utils import count_words


REQUIRED_SECTIONS = [
    "Executive Summary",
    "Understanding of RFP",
    "Proposed Solution Approach",
    "Functional and Technical Coverage",
    "Security and Compliance Approach",
    "Implementation Plan",
    "Risk and Mitigation",
    "Conclusion and Next Steps",
]

STRONG_CLAIM_KEYWORDS = [
    "ISO",
    "CMMI",
    "CERT-In",
    "STQC",
    "guaranteed",
    "fully compliant",
    "100%",
    "certified",
    "empanelled",
    "24x7",
    "unlimited",
]


def evaluate_draft_quality(db: Session, rfp_id: int) -> dict:
    sections = db.query(RFPDraftSection).filter(RFPDraftSection.rfp_id == rfp_id).order_by(RFPDraftSection.section_order).all()
    checks = []

    found_titles = {section.section_title for section in sections}
    for title in REQUIRED_SECTIONS:
        if title not in found_titles:
            checks.append(_check("missing_section", "warning", f"Missing section: {title}"))

    for section in sections:
        content = section.section_content or ""
        if not content.strip():
            checks.append(_check("empty_section", "warning", f"Section is empty: {section.section_title}"))
        if _contains_duplicate_heading(content, section.section_title):
            checks.append(_check("duplicate_heading", "review", f"Duplicate heading detected in {section.section_title}"))
        if _contains_markdown_artifacts(content):
            checks.append(_check("markdown_artifacts", "review", f"Markdown artifacts detected in {section.section_title}"))
        if section_contains_invalid_content(content):
            checks.append(_check("infrastructure_error_saved_as_content", "fail", f"Infrastructure error text detected in {section.section_title}"))
        if count_words(content) > 900:
            checks.append(_check("overlong_section", "review", f"Section exceeds 900 words: {section.section_title}"))

        strong_claims = _strong_claims(content)
        if strong_claims:
            checks.append(
                _check(
                    "unsupported_strong_claim",
                    "review",
                    f"Potential strong claims in {section.section_title}: {', '.join(strong_claims)}",
                )
            )

    checks.append(_check("human_review_required", "required", "Human proposal team review is required before use."))
    return {"overall_status": "needs_human_review", "checks": checks}


def _check(name: str, status: str, message: str) -> dict[str, str]:
    return {"name": name, "status": status, "message": message}


def _contains_duplicate_heading(content: str, section_title: str) -> bool:
    normalized_title = re.sub(r"[^a-z0-9]+", " ", section_title.lower()).strip()
    for line in content.splitlines():
        normalized_line = re.sub(r"[^a-z0-9]+", " ", line.lower()).strip()
        if normalized_line == normalized_title:
            return True
    return False


def _contains_markdown_artifacts(content: str) -> bool:
    return bool(re.search(r"(^#{1,6}\s)|(\*\*.*\*\*)|(`[^`]+`)|(^\s*\|.*\|\s*$)", content, re.MULTILINE))


def _strong_claims(content: str) -> list[str]:
    found = []
    lowered = content.lower()
    for keyword in STRONG_CLAIM_KEYWORDS:
        if keyword.lower() in lowered:
            found.append(keyword)
    return found
