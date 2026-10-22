from __future__ import annotations

import argparse
import sys
from pathlib import Path

from issue_repro import __version__
from issue_repro.errors import FetchError, UserError
from issue_repro.github import fetch_issue, parse_issue_ref
from issue_repro.pack import pack_repro
from issue_repro.template import TEMPLATE_FILES, write_repro

_EPILOG = """\
examples:
  issue-repro init
  issue-repro from-issue owner/repo#123
  issue-repro from-issue https://github.com/owner/repo/issues/123
  issue-repro pack
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="issue-repro",
        description="Create a minimal reproduction folder for a GitHub issue and zip it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOG,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"issue-repro {__version__}",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init_cmd = commands.add_parser("init", help="Write a blank repro/ template")
    _add_dir(init_cmd)
    init_cmd.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Replace template files if they already exist",
    )

    from_cmd = commands.add_parser(
        "from-issue",
        help="Fill repro/ from a GitHub issue",
    )
    from_cmd.add_argument(
        "issue",
        help="OWNER/REPO#N or a github.com issue URL",
    )
    _add_dir(from_cmd)
    from_cmd.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Replace template files if they already exist",
    )

    pack_cmd = commands.add_parser("pack", help="Zip repro/ to issue-repro-<slug>.zip")
    _add_dir(pack_cmd)
    pack_cmd.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Zip path to write (default: issue-repro-<slug>.zip)",
    )
    return parser


def _add_dir(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--dir",
        "-d",
        default=Path("repro"),
        type=Path,
        help="Reproduction directory (default: repro)",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return _exit_code(exc)

    try:
        if args.command == "init":
            return cmd_init(args.dir, force=args.force)
        if args.command == "from-issue":
            return cmd_from_issue(args.issue, args.dir, force=args.force)
        if args.command == "pack":
            return cmd_pack(args.dir, args.output)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"error: unknown command {args.command}", file=sys.stderr)
    return 2


def cmd_init(directory: Path, *, force: bool) -> int:
    write_repro(directory, force=force)
    shown = _display(directory)
    print(f"Wrote {shown} ({len(TEMPLATE_FILES)} files).")
    print("Next: edit repro.py in that folder, then run `issue-repro pack`.")
    return 0


def cmd_from_issue(spec: str, directory: Path, *, force: bool) -> int:
    ref = parse_issue_ref(spec)
    try:
        issue = fetch_issue(ref)
    except FetchError as exc:
        print(f"error: could not fetch {ref.short}: {exc}", file=sys.stderr)
        write_repro(directory, force=force, ref=ref, fetch_error=str(exc))
        shown = _display(directory)
        print(f"Wrote a blank template to {shown} and recorded the error in README.md.")
        return 1

    write_repro(directory, force=force, ref=ref, issue=issue)
    print(f"Wrote {_display(directory)} from {ref.short}.")
    summary = issue.title or "(no title)"
    if len(summary) > 120:
        summary = summary[:117] + "..."
    print(f"Summary: {summary}")
    print("Next: edit repro.py in that folder, then run `issue-repro pack`.")
    return 0


def cmd_pack(directory: Path, output: Path | None) -> int:
    result = pack_repro(directory, output)
    print(f"Wrote {result.path.as_posix()} ({result.size} bytes, {result.file_count} files).")
    return 0


def _display(path: Path) -> str:
    text = path.as_posix()
    return text if text.endswith("/") else text + "/"


def _exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    print(str(code), file=sys.stderr)
    return 1
