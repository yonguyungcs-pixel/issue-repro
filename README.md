**English** · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md)

# issue-repro

`issue-repro` builds a small folder you can hand to someone else when a GitHub issue is hard to reproduce. The folder holds a script, a note about the environment, and a place for expected and actual results. `pack` zips that folder so you can attach it to the issue.

Python 3.10 or newer. The command uses the standard library only.

## Install

From a checkout of this repository:

```bash
pip install -e .
issue-repro --version
```

`pip` registers the `issue-repro` console script. `issue-repro 0.1.0` is the current release.

## Commands

### init

Write a blank `repro/` template:

```bash
issue-repro init
```

| File | What it is for |
| --- | --- |
| `README.md` | Summary, steps, and how to run the script |
| `environment.md` | OS, Python version, and anything else that matters |
| `requirements.txt` | Packages to pin |
| `repro.py` | Smallest program that still shows the bug. It exits 1 until you change it |
| `EXPECTED.txt` | What should happen |
| `ACTUAL.txt` | What happens instead |

`--dir` picks a different folder name. `--force` replaces the template files and leaves any extra files you added in place.

### from-issue

Fill the same folder from a GitHub issue:

```bash
issue-repro from-issue OWNER/REPO#123
issue-repro from-issue https://github.com/OWNER/REPO/issues/123
```

The issue title becomes the summary. The issue body becomes the steps. Public issues work with no token. When `GITHUB_TOKEN` or `GH_TOKEN` is set, the command sends it as a bearer token. The token stays in that header. The folder and the zip are written without it.

If GitHub cannot be reached, the command still writes the blank template and records the error at the top of `repro/README.md`.

### pack

```bash
issue-repro pack
```

This writes `issue-repro-<slug>.zip` in the current directory. The slug is `owner-repo-123` when the folder came from an issue. Otherwise it is the project directory name. `-o path.zip` chooses the output file. The archive contains the `repro/` directory.

## Example

```bash
issue-repro from-issue pallets/flask#1
# edit repro/repro.py so it fails while the bug still happens
python repro/repro.py
issue-repro pack
```

The zip is named `issue-repro-pallets-flask-1.zip`. Attach it to the issue, or keep it locally.

## Screenshots

These are terminal sessions from this version of the command.

`issue-repro --version` and `issue-repro --help`:

![issue-repro --version and --help](docs/screenshots/help.png)

`issue-repro init` and the resulting `repro/` tree (`repro.py` exits 1):

![issue-repro init and the repro tree](docs/screenshots/init.png)

`issue-repro from-issue pallets/flask#1`, then the README it wrote:

![from-issue against the public Flask issue](docs/screenshots/from-issue.png)

`issue-repro pack` and the zip it wrote:

![issue-repro pack writing the zip](docs/screenshots/pack.png)

## Token handling

Export `GITHUB_TOKEN` or `GH_TOKEN` when you need a higher API rate limit or a private issue your account can already read. `GITHUB_TOKEN` wins when both are set. The value is sent only as an `Authorization` header, and it is removed from issue text and error text before anything is written.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

## 中文简介

`issue-repro` 把一个 GitHub issue 收成可以交给别人的 `repro/` 目录：里面有复现脚本、环境说明，以及期望结果和实际结果。`pack` 再把这个目录打成 zip，方便附在 issue 上。

```bash
pip install -e .
issue-repro init
issue-repro from-issue OWNER/REPO#123
issue-repro pack
```

- `init` 写入空白模板。`repro.py` 在你改完之前以退出码 1 结束。
- `from-issue` 用 issue 标题填写摘要，用正文填写步骤。公开 issue 不需要 token。拉取失败时仍会写入模板，并把错误记在 `repro/README.md`。
- `pack` 生成 `issue-repro-<slug>.zip`。

完整说明：[简体中文](README.zh-CN.md)、[繁體中文](README.zh-TW.md)、[日本語](README.ja.md)。

## License

[MIT](LICENSE)
