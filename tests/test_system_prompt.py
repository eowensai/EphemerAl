# audit-allowlist: contains forbidden-term list for testing
from pathlib import Path
import re

FORBIDDEN_ORG_TERMS = [
    r"University of Washington",
    r"\bUW\b",
    r"\bHFS\b",
    r"StarRez",
    r"Transact",
    r"Workday",
    r"SharePoint",
    r"OneDrive",
    r"\bTeams\b",
    r"student conduct",
    r"Title IX",
    r"\bFERPA\b",
    r"\bADA\b",
]


def test_system_prompt_has_no_forbidden_org_terms() -> None:
    content = Path("system_prompt_template.md").read_text(encoding="utf-8")
    for pattern in FORBIDDEN_ORG_TERMS:
        assert re.search(pattern, content, flags=re.IGNORECASE) is None, (
            f"Forbidden organization-specific term found: {pattern}"
        )


def test_system_prompt_includes_current_time_placeholder() -> None:
    content = Path("system_prompt_template.md").read_text(encoding="utf-8")
    assert "${current_time_local}" in content


def test_organization_example_exists_and_has_bracketed_placeholders() -> None:
    example_path = Path("examples/system_prompt.organization.example.md")
    assert example_path.exists()
    content = example_path.read_text(encoding="utf-8")

    for placeholder in ["[Your Organization]", "[Internal Systems]", "[Policy Areas]"]:
        assert placeholder in content
