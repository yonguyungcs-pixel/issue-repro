import json
from email.message import Message
from unittest.mock import patch
from urllib.error import URLError

import pytest

from issue_repro.errors import FetchError, UserError
from issue_repro.github import FETCH_TIMEOUT, fetch_issue, github_token, parse_issue_ref
from tests.support import Response, http_error


def test_parse_short_form_preserves_case():
    ref = parse_issue_ref("  Pallets/Flask#12. ")
    assert ref.owner == "Pallets"
    assert ref.repo == "Flask"
    assert ref.number == 12
    assert ref.short == "Pallets/Flask#12"
    assert ref.api_url == "https://api.github.com/repos/Pallets/Flask/issues/12"
    assert ref.slug == "pallets-flask-12"


@pytest.mark.parametrize(
    "spec",
    [
        "https://github.com/acme/widgets/issues/8",
        "http://github.com/acme/widgets/issues/8",
        "https://www.github.com/acme/widgets/issues/8/",
        "https://github.com/acme/widgets/issues/8#issuecomment-9",
        "https://github.com/acme/widgets/issues/8?utm_source=email",
        "https://GitHub.com/acme/widgets/pull/8",
        "github.com/acme/widgets/issues/8",
    ],
)
def test_parse_urls(spec):
    ref = parse_issue_ref(spec)
    assert (ref.owner, ref.repo, ref.number) == ("acme", "widgets", 8)


def test_parse_hyphen_owner_and_dotted_repo():
    ref = parse_issue_ref("my-org/my.repo_name#3")
    assert ref.owner == "my-org"
    assert ref.repo == "my.repo_name"
    assert ref.number == 3


@pytest.mark.parametrize(
    "spec",
    [
        "",
        "not a ref",
        "owner/repo",
        "owner/repo#0",
        "owner/#1",
        "https://gitlab.com/acme/widgets/issues/1",
        "https://user:testtoken_secret@github.com/acme/widgets/issues/1",
        "https://github.com/acme/widgets/issues/1?token=testtoken_secret",
        "acme/../widgets#1",
        "acme/..#1",
    ],
)
def test_parse_rejects_bad_specs(spec):
    with pytest.raises(UserError):
        parse_issue_ref(spec)


def test_fetch_success_without_token():
    payload = {
        "title": "Button stays disabled",
        "body": "1. Open the page\n2. Click save",
        "state": "open",
        "html_url": "https://github.com/acme/widgets/issues/5",
    }
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["auth"] = request.get_header("Authorization")
        seen["accept"] = request.get_header("Accept")
        seen["agent"] = request.get_header("User-agent")
        seen["api"] = request.get_header("X-github-api-version")
        return Response(payload)

    ref = parse_issue_ref("acme/widgets#5")
    with patch("issue_repro.github.urlopen", fake_urlopen):
        issue = fetch_issue(ref)

    assert seen["url"] == ref.api_url
    assert seen["timeout"] == FETCH_TIMEOUT
    assert seen["auth"] is None
    assert seen["accept"] == "application/vnd.github+json"
    assert seen["agent"] == "issue-repro/0.1.0"
    assert seen["api"] == "2022-11-28"
    assert issue.title == "Button stays disabled"
    assert "Click save" in issue.body
    assert issue.state == "open"
    assert issue.html_url.endswith("/issues/5")


def test_null_body_and_flattened_title():
    payload = {"title": "  spaced \n title ", "body": None, "state": "closed"}

    def fake_urlopen(request, timeout):
        return Response(payload)

    with patch("issue_repro.github.urlopen", fake_urlopen):
        issue = fetch_issue(parse_issue_ref("acme/widgets#5"))
    assert issue.title == "spaced title"
    assert issue.body == ""
    assert issue.state == "closed"


def test_bearer_token_from_github_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "testtoken_abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setenv("GH_TOKEN", "testtoken_other_token_should_not_win12")
    seen = {}

    def fake_urlopen(request, timeout):
        seen["auth"] = request.get_header("Authorization")
        return Response({"title": "t", "body": "ok"})

    with patch("issue_repro.github.urlopen", fake_urlopen):
        fetch_issue(parse_issue_ref("acme/widgets#5"))
    assert seen["auth"] == "Bearer testtoken_abcdefghijklmnopqrstuvwxyz"


def test_gh_token_used_when_github_token_missing(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "testtoken_from_gh_cli_token_value")
    seen = {}

    def fake_urlopen(request, timeout):
        seen["auth"] = request.get_header("Authorization")
        return Response({"title": "t", "body": ""})

    with patch("issue_repro.github.urlopen", fake_urlopen):
        fetch_issue(parse_issue_ref("acme/widgets#5"))
    assert seen["auth"] == "Bearer testtoken_from_gh_cli_token_value"


def test_whitespace_token_is_refused(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "testtoken_has a space")
    with patch("issue_repro.github.urlopen", side_effect=AssertionError("network")):
        with pytest.raises(FetchError, match="whitespace"):
            fetch_issue(parse_issue_ref("acme/widgets#5"))


def test_token_scrubbed_from_issue_text(monkeypatch):
    secret = "testtoken_super_secret_value_123456"
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    payload = {
        "title": f"leak {secret}",
        "body": f"body {secret}",
        "state": "open",
        "html_url": "https://github.com/acme/widgets/issues/5",
    }
    with patch("issue_repro.github.urlopen", lambda request, timeout: Response(payload)):
        issue = fetch_issue(parse_issue_ref("acme/widgets#5"))
    assert secret not in issue.title
    assert secret not in issue.body
    assert "***" in issue.title
    assert "***" in issue.body


def test_http_error_includes_status_and_message():
    error = http_error(404, json.dumps({"message": "Not Found"}).encode())
    with patch("issue_repro.github.urlopen", side_effect=error):
        with pytest.raises(FetchError, match="HTTP 404") as caught:
            fetch_issue(parse_issue_ref("acme/widgets#5"))
    assert "Not Found" in str(caught.value)


def test_rate_limit_hint():
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    error = http_error(403, json.dumps({"message": "limit"}).encode(), headers)
    with patch("issue_repro.github.urlopen", side_effect=error):
        with pytest.raises(FetchError, match="Rate limit"):
            fetch_issue(parse_issue_ref("acme/widgets#5"))


def test_rate_limit_error_scrubs_token(monkeypatch):
    secret = "testtoken_rate_limit_secret_value"
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    error = http_error(403, json.dumps({"message": f"nope {secret}"}).encode(), headers)
    with patch("issue_repro.github.urlopen", side_effect=error):
        with pytest.raises(FetchError) as caught:
            fetch_issue(parse_issue_ref("acme/widgets#5"))
    assert secret not in str(caught.value)
    assert "***" in str(caught.value)


def test_network_error():
    with patch("issue_repro.github.urlopen", side_effect=URLError("name lookup failed")):
        with pytest.raises(FetchError, match="Could not reach"):
            fetch_issue(parse_issue_ref("acme/widgets#5"))


def test_bad_json():
    with patch("issue_repro.github.urlopen", lambda request, timeout: Response(b"not-json")):
        with pytest.raises(FetchError, match="unreadable"):
            fetch_issue(parse_issue_ref("acme/widgets#5"))


def test_unexpected_payload():
    with patch("issue_repro.github.urlopen", lambda request, timeout: Response({"nope": True})):
        with pytest.raises(FetchError, match="unexpected"):
            fetch_issue(parse_issue_ref("acme/widgets#5"))


def test_oversized_response():
    with patch(
        "issue_repro.github.urlopen",
        lambda request, timeout: Response(b"x" * (2_000_001)),
    ):
        with pytest.raises(FetchError, match="2 MB"):
            fetch_issue(parse_issue_ref("acme/widgets#5"))


def test_redirect_off_api_host():
    response = Response({"title": "x", "body": ""}, url="https://evil.example/steal")
    with patch("issue_repro.github.urlopen", lambda request, timeout: response):
        with pytest.raises(FetchError, match="redirected"):
            fetch_issue(parse_issue_ref("acme/widgets#5"))


def test_pull_url_uses_issues_api():
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        return Response(
            {
                "title": "PR title",
                "body": "diff",
                "html_url": "https://github.com/acme/widgets/pull/8",
            }
        )

    with patch("issue_repro.github.urlopen", fake_urlopen):
        issue = fetch_issue(parse_issue_ref("https://github.com/acme/widgets/pull/8"))
    assert seen["url"] == "https://api.github.com/repos/acme/widgets/issues/8"
    assert issue.html_url.endswith("/pull/8")


def test_github_token_helper_none(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert github_token() is None
