import os
import subprocess
import sys
from pathlib import Path

from issue_repro import __version__
from issue_repro.cli import main


def test_version_matches_pyproject():
    pyproject = Path(__file__).resolve().parents[1].joinpath("pyproject.toml").read_text()
    assert 'version = "0.1.0"' in pyproject
    assert __version__ == "0.1.0"


def test_help_lists_commands(capsys):
    assert main(["--help"]) == 0
    output = capsys.readouterr().out
    assert "init" in output
    assert "from-issue" in output
    assert "pack" in output
    assert "OWNER/REPO#N" in output or "owner/repo#123" in output


def test_version_flag(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"issue-repro {__version__}"


def test_missing_command_exits_with_usage(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_module_entrypoint():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env.pop("GITHUB_TOKEN", None)
    env.pop("GH_TOKEN", None)
    result = subprocess.run(
        [sys.executable, "-m", "issue_repro", "--version"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "issue-repro 0.1.0"
