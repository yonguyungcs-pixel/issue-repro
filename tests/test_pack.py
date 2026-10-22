import zipfile
from pathlib import Path
from unittest.mock import patch

from issue_repro.cli import main
from issue_repro.sanitize import slugify
from tests.support import Response


def _init(tmp_path: Path) -> Path:
    directory = tmp_path / "repro"
    assert main(["init", "--dir", str(directory)]) == 0
    return directory


def test_pack_uses_project_directory_as_slug(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    directory = _init(tmp_path)
    assert main(["pack", "--dir", str(directory)]) == 0
    archive = tmp_path / f"issue-repro-{slugify(tmp_path.name)}.zip"
    assert archive.is_file()
    assert archive.name in capsys.readouterr().out
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        assert "repro/README.md" in names
        assert "repro/repro.py" in names
        assert "repro/environment.md" in names
        assert "repro/requirements.txt" in names
        assert "repro/EXPECTED.txt" in names
        assert "repro/ACTUAL.txt" in names
        assert all("\\" not in name for name in names)
        assert zipped.read("repro/README.md").decode().startswith("# Reproduction")
        info = zipped.getinfo("repro/README.md")
        assert info.compress_type == zipfile.ZIP_DEFLATED


def test_pack_default_name_follows_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    payload = {"title": "Broken", "body": "Step one", "state": "open"}

    def fake_urlopen(request, timeout):
        return Response(payload)

    with patch("issue_repro.github.urlopen", fake_urlopen):
        assert main(["from-issue", "acme/widgets#5"]) == 0
    assert main(["pack"]) == 0
    archive = tmp_path / "issue-repro-acme-widgets-5.zip"
    assert archive.is_file()
    assert "issue-repro-acme-widgets-5.zip" in capsys.readouterr().out
    with zipfile.ZipFile(archive) as zipped:
        readme = zipped.read("repro/README.md").decode()
    assert "Broken" in readme
    assert "Step one" in readme


def test_pack_after_failed_fetch_keeps_issue_slug(tmp_path, monkeypatch):
    from urllib.error import URLError

    monkeypatch.chdir(tmp_path)
    with patch("issue_repro.github.urlopen", side_effect=URLError("offline")):
        assert main(["from-issue", "acme/widgets#9"]) == 1
    assert main(["pack"]) == 0
    assert (tmp_path / "issue-repro-acme-widgets-9.zip").is_file()


def test_pack_missing_directory(tmp_path, capsys):
    assert main(["pack", "--dir", str(tmp_path / "repro")]) == 1
    assert "does not exist" in capsys.readouterr().err


def test_pack_missing_readme(tmp_path, capsys):
    directory = tmp_path / "repro"
    directory.mkdir()
    assert main(["pack", "--dir", str(directory)]) == 1
    assert "README.md" in capsys.readouterr().err


def test_pack_refuses_output_inside_repro(tmp_path, capsys):
    directory = _init(tmp_path)
    target = directory / "packed.zip"
    assert main(["pack", "--dir", str(directory), "--output", str(target)]) == 1
    assert "inside" in capsys.readouterr().err
    assert not target.exists()


def test_pack_includes_extra_files_and_skips_junk(tmp_path):
    directory = _init(tmp_path)
    (directory / "notes.txt").write_text("hello\n", encoding="utf-8")
    nested = directory / "logs"
    nested.mkdir()
    (nested / "run.txt").write_text("trace\n", encoding="utf-8")
    cache = directory / "__pycache__"
    cache.mkdir()
    (cache / "repro.cpython-312.pyc").write_bytes(b"pyc")
    (directory / "skip.pyc").write_bytes(b"pyc")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret\n", encoding="utf-8")
    link = directory / "linked.txt"
    link.symlink_to(outside)

    archive_path = tmp_path / "pack.zip"
    assert main(["pack", "--dir", str(directory), "--output", str(archive_path)]) == 0
    with zipfile.ZipFile(archive_path) as zipped:
        names = set(zipped.namelist())
    assert "repro/notes.txt" in names
    assert "repro/logs/run.txt" in names
    assert not any("pyc" in name or "__pycache__" in name or "linked" in name for name in names)
    blob = archive_path.read_bytes()
    assert b"secret" not in blob


def test_pack_overwrites_existing_zip(tmp_path):
    directory = _init(tmp_path)
    archive_path = tmp_path / "pack.zip"
    archive_path.write_bytes(b"old")
    assert main(["pack", "--dir", str(directory), "--output", str(archive_path)]) == 0
    assert zipfile.is_zipfile(archive_path)


def test_custom_dir_slug_and_archive_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--dir", "case"]) == 0
    assert main(["pack", "--dir", "case"]) == 0
    archive = tmp_path / "issue-repro-case.zip"
    assert archive.is_file()
    with zipfile.ZipFile(archive) as zipped:
        assert "case/repro.py" in zipped.namelist()


def test_token_never_enters_the_zip(tmp_path, monkeypatch):
    secret = "testtoken_pack_must_not_contain_this"
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    monkeypatch.chdir(tmp_path)
    payload = {"title": f"title {secret}", "body": f"body {secret}", "state": "open"}

    def fake_urlopen(request, timeout):
        from tests.test_github import Response

        assert request.get_header("Authorization") == f"Bearer {secret}"
        return Response(payload)

    with patch("issue_repro.github.urlopen", fake_urlopen):
        assert main(["from-issue", "acme/widgets#5"]) == 0
    assert main(["pack"]) == 0
    blob = (tmp_path / "issue-repro-acme-widgets-5.zip").read_bytes()
    assert secret.encode() not in blob
    readme = (tmp_path / "repro" / "README.md").read_text(encoding="utf-8")
    assert secret not in readme
