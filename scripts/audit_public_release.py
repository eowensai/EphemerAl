#!/usr/bin/env python3
"""Public release audit for repository hygiene.

Uses only Python standard library.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "artifacts",
    "dist",
    "build",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tar", ".mp4", ".mp3", ".woff", ".woff2",
}

ALLOWLIST_TERMS = {
    "EphemerAl",
    "EphemerAI",
    "Ollama",
    "Apache Tika",
    "localhost",
    "example.com",
    "test@example.com",
}

ALLOWLIST_FILE_SUBSTRINGS = {
    "tests/fixtures/",
    "scripts/audit_public_release.py",
}

SENTINEL = "# audit-allowlist: contains forbidden-term list for testing"

@dataclass
class Rule:
    category: str
    pattern: re.Pattern[str]
    high_confidence: bool = False


RULES: list[Rule] = [
    Rule("Organization/person identity terms", re.compile(r"\b(University of Washington|\bUW\b|\bHFS\b|StarRez|Transact|Workday|SharePoint|OneDrive|\bTeams\b|eowensai|day job|our team's sensitive)\b", re.IGNORECASE), high_confidence=True),
    Rule("Personal URLs/emails", re.compile(r"https?://(?:www\.)?github\.com/(?!ollama(?:/|$))[A-Za-z0-9_.-]+/?|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE), high_confidence=True),
    Rule("Secret-like patterns", re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,})"), high_confidence=True),
    Rule("Hardcoded old branding that should now be config-driven", re.compile(r"\bEphemeral Screenshot\.jpg\b|\bEphemeral%20Screenshot\.jpg\b|\bephemeral_logo_old\b", re.IGNORECASE)),
    Rule("Manual Modelfile/YAML/source-editing instructions in docs", re.compile(r"\b(edit|modify|open)\b.{0,80}\b(Modelfile|docker-compose\.yml|source code|yaml)\b", re.IGNORECASE)),
    Rule("Orphan/default-brand binary asset references where detectable", re.compile(r"\b(static/)?ephemeral_logo_old\.png\b|\bEphemeral(?:%20| )Screenshot\.jpg\b", re.IGNORECASE)),
    Rule("Privacy posture drift, such as OLLAMA_NO_CLOUD disabled by default", re.compile(r"OLLAMA_NO_CLOUD\s*(?:=|:)\s*(?:0|false|False)")),
]


def redact_secret(value: str) -> str:
    if len(value) <= 10:
        return value
    return value[:4] + "…" + value[-4:]


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
        if b"\x00" in chunk:
            return False
    except OSError:
        return False
    return True


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".venv")]
        for name in filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if any(part in rel for part in ALLOWLIST_FILE_SUBSTRINGS):
                continue
            if is_probably_text(path):
                yield path


def allowlisted(path: Path, line: str) -> bool:
    for term in ALLOWLIST_TERMS:
        if term in line:
            return True
    rel = path.relative_to(ROOT).as_posix()
    if rel == "tests/test_system_prompt.py":
        try:
            first = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        except Exception:
            return False
        if first == SENTINEL:
            return True
    return False


def main() -> int:
    findings: list[tuple[str, int, str, str, bool]] = []
    for path in iter_files(ROOT):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rule in RULES:
                for match in rule.pattern.finditer(line):
                    token = match.group(0)
                    if allowlisted(path, line):
                        continue
                    snippet = line.strip()
                    if rule.category == "Secret-like patterns":
                        snippet = snippet.replace(token, redact_secret(token))
                    findings.append((rel, lineno, snippet, rule.category, rule.high_confidence))

    if not findings:
        print("No findings.")
        return 0

    findings.sort()
    grouped: dict[str, list[tuple[str, int, str, bool]]] = {}
    for rel, lineno, snippet, category, high in findings:
        grouped.setdefault(category, []).append((rel, lineno, snippet, high))

    high_count = 0
    for category, items in grouped.items():
        print(f"\n[{category}] ({len(items)} findings)")
        for rel, lineno, snippet, high in items:
            high_count += 1 if high else 0
            print(f"- {rel}:{lineno}: {snippet}")

    return 2 if high_count else 1


if __name__ == "__main__":
    sys.exit(main())
