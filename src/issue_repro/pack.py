from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from issue_repro.errors import UserError
from issue_repro.sanitize import slugify

_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
_MARKER = re.compile(
    r"<!--\s*issue-repro-ref:\s*"
    r"([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})#([1-9]\d*)"
    r"\s*-->"
)


@dataclass(frozen=True)
class PackResult:
    path: Path
    file_count: int
    size: int


def pack_repro(repro_dir: Path, output: Path | None = None) -> PackResult:
    if not repro_dir.exists():
        raise UserError(
            f"{repro_dir} does not exist. Run `issue-repro init` or `issue-repro from-issue` first."
        )
    if not repro_dir.is_dir():
        raise UserError(f"{repro_dir} is not a directory.")
    readme = repro_dir / "README.md"
    if not readme.is_file():
        raise UserError(f"{repro_dir} has no README.md. Run `issue-repro init` first.")

    slug = issue_slug(readme) or directory_slug(repro_dir)
    destination = output if output is not None else Path(f"issue-repro-{slug}.zip")
    if destination.exists() and not destination.is_file():
        raise UserError(f"{destination} exists and is not a file.")

    dest_resolved = destination.resolve()
    repro_resolved = repro_dir.resolve()
    if dest_resolved == repro_resolved or repro_resolved in dest_resolved.parents:
        raise UserError(
            f"Refusing to write the zip inside {repro_dir}. "
            "Choose an output path outside that folder."
        )

    files = list_pack_files(repro_dir)
    root = archive_root(repro_dir)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UserError(f"Could not create {destination.parent}: {exc.strerror}") from exc

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                relative = path.relative_to(repro_dir)
                archive.write(path, (Path(root) / relative).as_posix())
        temporary.replace(destination)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise UserError(f"Could not write {destination}: {exc.strerror}") from exc
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return PackResult(path=destination, file_count=len(files), size=destination.stat().st_size)


def issue_slug(readme: Path) -> str | None:
    try:
        text = readme.read_text(encoding="utf-8")[:4000]
    except (OSError, UnicodeError):
        return None
    match = _MARKER.search(text)
    if match is None:
        return None
    return slugify(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")


def directory_slug(repro_dir: Path) -> str:
    resolved = repro_dir.resolve()
    if resolved.name.lower() == "repro":
        return slugify(resolved.parent.name)
    return slugify(resolved.name)


def archive_root(repro_dir: Path) -> str:
    return repro_dir.resolve().name or "repro"


def list_pack_files(repro_dir: Path) -> list[Path]:
    found: list[Path] = []
    for path in repro_dir.rglob("*"):
        if path.is_symlink():
            continue
        relative = path.relative_to(repro_dir)
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        if path.is_file() and path.suffix != ".pyc":
            found.append(path)
    found.sort(key=lambda item: item.relative_to(repro_dir).as_posix())
    return found
