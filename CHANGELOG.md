# Changelog

## 0.1.0 - 2026-10-22

- First release of the `issue-repro` command.
- `init` writes a `repro/` template: README, environment notes, requirements, a script that exits 1, and expected/actual notes.
- `from-issue` fills that template from a GitHub issue (`OWNER/REPO#N` or an issue URL). A failed fetch still writes the template and records the error in the README.
- `pack` zips the folder to `issue-repro-<slug>.zip`.
- `GITHUB_TOKEN` / `GH_TOKEN` are sent as a bearer token when set, and are kept out of the folder and the zip.
