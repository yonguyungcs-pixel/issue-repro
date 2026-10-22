from __future__ import annotations

import os
import re

_SLUG_UNSAFE = re.compile(r"[^a-z0-9._-]+")
_SLUG_DASHES = re.compile(r"-{2,}")


def slugify(value: str) -> str:
    """Filesystem-friendly slug. Empty input becomes ``repro``."""
    cleaned = _SLUG_UNSAFE.sub("-", value.strip().lower())
    cleaned = _SLUG_DASHES.sub("-", cleaned).strip("-.")
    return cleaned[:80] or "repro"


def scrub_secrets(text: str) -> str:
    """Remove GitHub tokens from text that will be written to disk."""
    if not text:
        return text
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name) or ""
        if len(value) >= 8:
            text = text.replace(value, "***")
    return text
