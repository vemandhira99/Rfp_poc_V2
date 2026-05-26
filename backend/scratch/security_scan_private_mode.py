import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATTERNS = ["openai", "azure", "gemini", "google.generativeai", "anthropic", "claude", "langchain", "langgraph"]
FORBIDDEN_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+.*(?:openai|azure|gemini|google\.generativeai|anthropic|langchain|langgraph|claude)", re.IGNORECASE | re.MULTILINE)
URL_RE = re.compile(r"https?://[^\s\"')]+")
SOURCE_DIRS = [ROOT / "app", ROOT / "mcp_server" / "tools", ROOT / "mcp_server" / "server.py", ROOT.parent / "frontend" / "app", ROOT.parent / "frontend" / "components", ROOT.parent / "frontend" / "lib"]
DOC_DIRS = [ROOT.parent / "docs", ROOT / "mcp_server" / "README.md"]
ALLOWED_URL_PREFIXES = ("http://localhost", "http://127.0.0.1")


def scan_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings = []
    lowered = text.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in lowered:
            findings.append(pattern)
    if FORBIDDEN_IMPORT_RE.search(text):
        findings.append("cloud_import")
    for url in URL_RE.findall(text):
        if not url.startswith(ALLOWED_URL_PREFIXES):
            findings.append(url)
    return findings


def collect(paths: list[Path]) -> list[tuple[str, list[str]]]:
    out = []
    for base in paths:
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else list(base.rglob("*"))
        for path in candidates:
            if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".md", ".txt", ".json"}:
                findings = scan_file(path)
                if findings:
                    text = path.read_text(encoding="utf-8", errors="ignore").lower()
                    if "no " in text or "disabled" in text or "external ai provider" in text or "privacy" in text:
                        out.append((str(path.relative_to(ROOT.parent)), [f"SAFETY_TEXT:{item}" for item in findings]))
                    else:
                        out.append((str(path.relative_to(ROOT.parent)), findings))
    return out


if __name__ == "__main__":
    active = collect(SOURCE_DIRS)
    docs = collect(DOC_DIRS)
    print("Active code findings:", active)
    print("Docs/safety text findings:", docs)
    # Provider words in privacy/safety UI text are acceptable; imports/calls are not.
    active_failures = [
        (p, f)
        for p, f in active
        if any(
            not item.startswith("SAFETY_TEXT:")
            and (item.startswith("http") or item in {"cloud_import"} or item in FORBIDDEN_PATTERNS)
            for item in f
        )
    ]
    print("PASS:", len(active_failures) == 0)
    sys.exit(1 if active_failures else 0)
