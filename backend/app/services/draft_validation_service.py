from app.models.rfp import RFPDraftSection
from app.services.ollama_health_service import is_infrastructure_error


INVALID_CONTENT_MARKERS = [
    "ollama is not running",
    "model is not available",
    "connection refused",
    "please start ollama",
    "error:",
    "traceback",
    "exception",
]


class DraftNotReadyError(ValueError):
    code = "DRAFT_NOT_READY"

    def __init__(self, message: str = "Draft is not ready for export. Please complete generation first.") -> None:
        super().__init__(message)
        self.message = message


def section_contains_invalid_content(content: str) -> bool:
    lowered = (content or "").lower()
    return any(marker in lowered for marker in INVALID_CONTENT_MARKERS)


def get_section_validation_issues(content: str) -> list[str]:
    issues: list[str] = []
    if section_contains_invalid_content(content):
        issues.append("contains_infrastructure_error_text")
    return issues


def validate_draft_sections(sections: list[RFPDraftSection]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if len(sections) != 8:
        issues.append("Draft must contain exactly 8 sections.")
    for section in sections:
        content = (section.section_content or "").strip()
        if not content:
            issues.append(f"Section {section.section_order} is empty.")
        if section_contains_invalid_content(content):
            issues.append(f"Section {section.section_order} contains infrastructure error text.")
    return (len(issues) == 0, issues)


def is_error_like_content(content: str) -> bool:
    return section_contains_invalid_content(content) or is_infrastructure_error(content)
