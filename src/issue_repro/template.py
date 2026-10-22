from __future__ import annotations

import platform
from pathlib import Path

from issue_repro.errors import UserError
from issue_repro.github import Issue, IssueRef
from issue_repro.sanitize import scrub_secrets

TEMPLATE_FILES = (
    "README.md",
    "environment.md",
    "requirements.txt",
    "repro.py",
    "EXPECTED.txt",
    "ACTUAL.txt",
)

_REPRO_PY = '''\
#!/usr/bin/env python3
"""Smallest program that still shows the bug.

Exit 0 when the bug is fixed. Exit 1 while it still happens.
"""

from __future__ import annotations

import sys


def main() -> int:
    print("TODO: replace this with the smallest code that shows the bug")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

_REQUIREMENTS = """\
# Packages required to run repro.py.
# Pin versions so the next person hits the same bug.
#
# example==1.2.3
"""

_EXPECTED = """\
Describe what should happen.

repro.py should exit 0 once the bug is fixed.
"""

_ACTUAL = """\
Describe what actually happens. Paste command output here.

repro.py exits 1 while the bug still happens.
"""


def prepare_directory(directory: Path, *, force: bool) -> None:
    if directory.exists() and not directory.is_dir():
        raise UserError(f"{_display(directory)} exists and is not a directory.")
    if directory.is_dir() and not force:
        present = [name for name in TEMPLATE_FILES if (directory / name).exists()]
        if present:
            names = ", ".join(present)
            raise UserError(
                f"{_display(directory)} already has template files ({names}). "
                "Pass --force to replace them."
            )
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UserError(f"Could not create {directory}: {exc.strerror}") from exc


def write_repro(
    directory: Path,
    *,
    force: bool,
    ref: IssueRef | None = None,
    issue: Issue | None = None,
    fetch_error: str | None = None,
) -> None:
    prepare_directory(directory, force=force)
    files = {
        "README.md": render_readme(ref=ref, issue=issue, fetch_error=fetch_error),
        "environment.md": render_environment(),
        "requirements.txt": _REQUIREMENTS,
        "repro.py": _REPRO_PY,
        "EXPECTED.txt": _EXPECTED,
        "ACTUAL.txt": _ACTUAL,
    }
    for name, content in files.items():
        path = directory / name
        try:
            path.write_text(content, encoding="utf-8", newline="\n")
        except OSError as exc:
            raise UserError(f"Could not write {path}: {exc.strerror}") from exc


def render_environment() -> str:
    return (
        "# Environment\n"
        "\n"
        f"- OS: {platform.platform()}\n"
        f"- Python: {platform.python_version()}\n"
        "- Packages: see requirements.txt\n"
        "\n"
        "Add anything else a maintainer would need (locale, architecture, services).\n"
        "Leave secrets out of this file.\n"
    )


def render_readme(
    *,
    ref: IssueRef | None,
    issue: Issue | None,
    fetch_error: str | None,
) -> str:
    lines: list[str] = []
    if ref is not None:
        lines.append(f"<!-- issue-repro-ref: {ref.short} -->")
    lines.append("# Reproduction")
    lines.append("")
    if ref is not None:
        url = issue.html_url if issue is not None else ref.html_url
        lines.append(f"- Issue: {ref.short}")
        lines.append(f"- URL: {url}")
    else:
        lines.append("- Issue:")
    state = issue.state if issue is not None else ""
    if state:
        lines.append(f"- State: {state}")
    title = issue.title if issue is not None else ""
    lines.append(f"- Summary: {title}".rstrip())
    lines.append("")
    if fetch_error:
        cleaned = scrub_secrets(fetch_error).strip() or "unknown error"
        for line in cleaned.splitlines():
            lines.append(f"> {line}" if line else ">")
        lines.append(">")
        lines.append("> This folder is a blank template. Fill it in by hand.")
        lines.append("")
    lines.append("## Steps")
    lines.append("")
    body = issue.body if issue is not None else ""
    if body.strip():
        lines.append(body.strip("\n"))
    else:
        lines.append("1.")
    lines.extend(
        [
            "",
            "## Expected",
            "",
            "See [EXPECTED.txt](EXPECTED.txt).",
            "",
            "## Actual",
            "",
            "See [ACTUAL.txt](ACTUAL.txt).",
            "",
            "## Run",
            "",
            "```bash",
            "python repro.py",
            "```",
            "",
            "Exit 0 when the bug is fixed. Exit 1 while it still happens.",
            "",
        ]
    )
    return "\n".join(lines)


def _display(path: Path) -> str:
    text = path.as_posix()
    return text if text.endswith("/") else text + "/"
