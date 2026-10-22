#!/usr/bin/env python3
"""Capture real ``issue-repro`` sessions into ``docs/screenshots``.

Requires ``issue-repro`` on PATH and the Pillow package::

    pip install -e .
    pip install pillow
    python scripts/capture_screenshots.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
ISSUE = "pallets/flask#1"
FONT_PATH = Path("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf")
FONT_BOLD_PATH = Path("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf")
WIDTH = 96


def main() -> None:
    binary = shutil.which("issue-repro")
    if binary is None:
        raise SystemExit("issue-repro is not on PATH. Run: pip install -e .")
    OUT.mkdir(parents=True, exist_ok=True)

    help_text = "\n".join(
        [
            run("issue-repro --version", [binary, "--version"]),
            run("issue-repro --help", [binary, "--help"]),
        ]
    )
    render(help_text, "issue-repro --version / --help", OUT / "help.png")

    with tempfile.TemporaryDirectory(prefix="issue-repro-init-") as raw:
        init_dir = Path(raw)
        init_text = "\n".join(
            [
                run("issue-repro init", [binary, "init"], init_dir),
                run(
                    "find repro -type f | sort",
                    ["bash", "-lc", "find repro -type f | sort"],
                    init_dir,
                ),
                run(
                    "python repro/repro.py; echo exit:$?",
                    ["bash", "-lc", "python repro/repro.py; echo exit:$?"],
                    init_dir,
                ),
            ]
        )
        render(init_text, "issue-repro init", OUT / "init.png")

    with tempfile.TemporaryDirectory(prefix="issue-repro-issue-") as raw:
        issue_dir = Path(raw)
        filled = "\n".join(
            [
                run(
                    f"issue-repro from-issue {ISSUE}",
                    [binary, "from-issue", ISSUE],
                    issue_dir,
                ),
                run(
                    "fold -s -w 88 repro/README.md",
                    ["bash", "-lc", "fold -s -w 88 repro/README.md"],
                    issue_dir,
                ),
            ]
        )
        render(filled, f"issue-repro from-issue {ISSUE}", OUT / "from-issue.png")
        packed = "\n".join(
            [
                run("issue-repro pack", [binary, "pack"], issue_dir),
                run(
                    "ls -l issue-repro-pallets-flask-1.zip",
                    ["bash", "-lc", "ls -l issue-repro-pallets-flask-1.zip"],
                    issue_dir,
                ),
                run(
                    "python -m zipfile -l issue-repro-pallets-flask-1.zip",
                    ["bash", "-lc", "python -m zipfile -l issue-repro-pallets-flask-1.zip"],
                    issue_dir,
                ),
            ]
        )
        render(packed, "issue-repro pack", OUT / "pack.png")

    _reject_token_leaks()
    print(f"Wrote screenshots in {OUT}")


def run(display: str, argv: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    body = (result.stdout + result.stderr).strip("\n")
    shown = f"$ {display}"
    if body:
        shown = f"{shown}\n{body}"
    if result.returncode != 0:
        raise SystemExit(f"command failed ({result.returncode}): {display}\n{shown}")
    return shown


def render(text: str, title: str, dest: Path) -> None:
    font = ImageFont.truetype(str(FONT_PATH), 18)
    bold = ImageFont.truetype(str(FONT_BOLD_PATH), 18)
    lines = _wrap(text)
    line_height = 26
    pad_x = 28
    pad_y = 18
    header = 44
    widest = max(_line_px(line, font, bold) for line in lines)
    width = max(860, widest + pad_x * 2)
    height = header + pad_y * 2 + line_height * len(lines)

    image = Image.new("RGB", (width, height), "#0d1117")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, header), fill="#161b22")
    draw.line((0, header, width, header), fill="#30363d")
    for index, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        left = 18 + index * 22
        draw.ellipse((left, 16, left + 12, 28), fill=color)
    title_width = font.getbbox(title)[2]
    draw.text(((width - title_width) / 2, 12), title, font=font, fill="#8b949e")

    y = header + pad_y
    dollar = bold.getbbox("$")[2]
    for line in lines:
        if line.startswith("$ "):
            draw.text((pad_x, y), "$", font=bold, fill="#3fb950")
            draw.text((pad_x + dollar + 8, y), line[2:], font=bold, fill="#e6edf3")
        else:
            draw.text((pad_x, y), line, font=font, fill="#c9d1d9")
        y += line_height

    image.save(dest, format="PNG", optimize=True)


def _line_px(line: str, font: ImageFont.FreeTypeFont, bold: ImageFont.FreeTypeFont) -> int:
    if line.startswith("$ "):
        return bold.getbbox("$")[2] + 8 + bold.getbbox(line[2:] or " ")[2]
    return font.getbbox(line or " ")[2]


def _wrap(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        if len(raw) <= WIDTH:
            lines.append(raw)
            continue
        while len(raw) > WIDTH:
            lines.append(raw[:WIDTH])
            raw = raw[WIDTH:]
        lines.append(raw)
    return lines


def _reject_token_leaks() -> None:
    secrets = [os.environ.get("GITHUB_TOKEN") or "", os.environ.get("GH_TOKEN") or ""]
    secrets = [value for value in secrets if len(value) >= 8]
    if not secrets:
        return
    for path in OUT.glob("*.png"):
        blob = path.read_bytes()
        for secret in secrets:
            if secret.encode() in blob:
                path.unlink()
                raise SystemExit(f"refusing to keep {path.name}: it contains a GitHub token")


if __name__ == "__main__":
    main()
