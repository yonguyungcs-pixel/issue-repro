# Contributing

Thanks for looking at a bug or a patch.

## Setup

Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Runtime code stays on the standard library. `pytest` and `ruff` are development tools only.

## Checks

```bash
ruff check .
pytest
```

The GitHub Actions workflow runs those, then a smoke test: `issue-repro init` and `issue-repro pack`.

## Pull requests

- Describe the behavior change and how you checked it.
- Add or update a test when you change `init`, `from-issue`, or `pack`.
- Keep the version in `src/issue_repro/__init__.py` and `pyproject.toml` in sync. Bump it only when cutting a release, and add a `CHANGELOG.md` entry.
- Do not commit tokens, `.env` files, generated `repro/` folders, or zip packs.

## Screenshots

The pictures in `docs/screenshots/` are captured from real CLI output.

```bash
pip install pillow
python scripts/capture_screenshots.py
```

`issue-repro` needs to be on `PATH` (the editable install above does that). The script fetches a public GitHub issue, so it needs network access. It refuses to write a screenshot that contains `GITHUB_TOKEN` or `GH_TOKEN`.

## Secrets

`from-issue` reads `GITHUB_TOKEN` or `GH_TOKEN` from the environment and sends it only as an `Authorization` header. Do not put a token in an issue URL, a fixture, or a screenshot.
