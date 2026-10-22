import os
import platform
import stat
import subprocess
import sys
from unittest.mock import patch

from issue_repro.cli import main
from issue_repro.template import TEMPLATE_FILES
from tests.support import Response


def test_init_writes_template_and_script_exits_1(tmp_path, capsys):
    assert main(["init", "--dir", str(tmp_path / "repro")]) == 0
    message = capsys.readouterr().out
    assert "6 files" in message
    directory = tmp_path / "repro"
    for name in TEMPLATE_FILES:
        assert (directory / name).is_file()
    readme = (directory / "README.md").read_text(encoding="utf-8")
    assert "# Reproduction" in readme
    assert "- Issue:" in readme
    assert "issue-repro-ref" not in readme
    environment = (directory / "environment.md").read_text(encoding="utf-8")
    assert platform.python_version() in environment
    assert platform.platform() in environment
    script = directory / "repro.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "TODO" in result.stdout


def test_init_does_not_touch_the_network(tmp_path):
    with patch("issue_repro.github.urlopen", side_effect=AssertionError("network")):
        assert main(["init", "--dir", str(tmp_path / "repro")]) == 0


def test_init_refuses_to_overwrite_without_force(tmp_path, capsys):
    directory = tmp_path / "repro"
    assert main(["init", "--dir", str(directory)]) == 0
    (directory / "README.md").write_text("keep me\n", encoding="utf-8")
    assert main(["init", "--dir", str(directory)]) == 1
    assert "Pass --force" in capsys.readouterr().err
    assert (directory / "README.md").read_text(encoding="utf-8") == "keep me\n"


def test_force_replaces_template_and_keeps_extra_files(tmp_path):
    directory = tmp_path / "repro"
    assert main(["init", "--dir", str(directory)]) == 0
    extra = directory / "notes.txt"
    extra.write_text("keep\n", encoding="utf-8")
    (directory / "README.md").write_text("old\n", encoding="utf-8")
    assert main(["init", "--force", "--dir", str(directory)]) == 0
    assert extra.read_text(encoding="utf-8") == "keep\n"
    assert "old" not in (directory / "README.md").read_text(encoding="utf-8")


def test_init_rejects_a_file_at_the_target_path(tmp_path, capsys):
    target = tmp_path / "repro"
    target.write_text("file\n", encoding="utf-8")
    assert main(["init", "--dir", str(target)]) == 1
    assert "not a directory" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "file\n"


def test_from_issue_fills_summary_and_steps(tmp_path, capsys):
    payload = {
        "title": "Save button does nothing",
        "body": "Open settings.\nPress save.",
        "state": "open",
        "html_url": "https://github.com/acme/widgets/issues/5",
    }

    def fake_urlopen(request, timeout):
        return Response(payload, url="https://api.github.com/repos/acme/widgets/issues/5")

    with patch("issue_repro.github.urlopen", fake_urlopen):
        code = main(["from-issue", "acme/widgets#5", "--dir", str(tmp_path / "repro")])
    assert code == 0
    output = capsys.readouterr().out
    assert "acme/widgets#5" in output
    assert "Save button does nothing" in output
    readme = (tmp_path / "repro" / "README.md").read_text(encoding="utf-8")
    assert "<!-- issue-repro-ref: acme/widgets#5 -->" in readme
    assert "- Summary: Save button does nothing" in readme
    assert "Press save." in readme
    assert "- State: open" in readme
    assert "- URL: https://github.com/acme/widgets/issues/5" in readme


def test_from_issue_failure_still_writes_template(tmp_path, capsys):
    from urllib.error import URLError

    with patch("issue_repro.github.urlopen", side_effect=URLError("offline")):
        code = main(["from-issue", "acme/widgets#5", "--dir", str(tmp_path / "repro")])
    assert code == 1
    captured = capsys.readouterr()
    assert "could not fetch" in captured.err
    assert "blank template" in captured.out
    readme = (tmp_path / "repro" / "README.md").read_text(encoding="utf-8")
    assert "Could not reach the GitHub API" in readme
    assert "blank template" in readme
    assert "<!-- issue-repro-ref: acme/widgets#5 -->" in readme
    assert "- Summary:" in readme
    for name in TEMPLATE_FILES:
        assert (tmp_path / "repro" / name).is_file()


def test_invalid_issue_spec_writes_nothing(tmp_path, capsys):
    assert main(["from-issue", "nope", "--dir", str(tmp_path / "repro")]) == 1
    assert "Not a GitHub issue" in capsys.readouterr().err
    assert not (tmp_path / "repro").exists()


def test_fetch_error_is_reported_when_template_exists(tmp_path, capsys):
    from urllib.error import URLError

    directory = tmp_path / "repro"
    assert main(["init", "--dir", str(directory)]) == 0
    capsys.readouterr()
    with patch("issue_repro.github.urlopen", side_effect=URLError("offline")):
        code = main(["from-issue", "acme/widgets#5", "--dir", str(directory)])
    assert code == 1
    captured = capsys.readouterr()
    assert "could not fetch" in captured.err
    assert "--force" in captured.err
    assert "issue-repro-ref" not in (directory / "README.md").read_text(encoding="utf-8")


def test_fetch_failure_does_not_write_token(tmp_path, monkeypatch):
    from email.message import Message

    from tests.support import http_error

    secret = "testtoken_should_not_land_in_files_99"
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    error = http_error(403, f'{{"message":"denied {secret}"}}'.encode(), headers)
    with patch("issue_repro.github.urlopen", side_effect=error):
        assert main(["from-issue", "acme/widgets#5", "--dir", str(tmp_path / "repro")]) == 1
    blob = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "repro").iterdir())
    assert secret not in blob
    assert "***" in blob


def test_repro_py_is_a_regular_file(tmp_path):
    main(["init", "--dir", str(tmp_path / "repro")])
    mode = (tmp_path / "repro" / "repro.py").stat().st_mode
    assert stat.S_ISREG(mode)
    assert os.access(tmp_path / "repro" / "repro.py", os.R_OK)
