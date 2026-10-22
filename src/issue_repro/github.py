from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from issue_repro import __version__
from issue_repro.errors import FetchError, UserError
from issue_repro.sanitize import scrub_secrets, slugify

FETCH_TIMEOUT = 20
_MAX_BYTES = 2_000_000

_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"
_REPO = r"[A-Za-z0-9._-]{1,100}"
_NUMBER = r"[1-9]\d*"

_SHORT = re.compile(rf"^(?P<owner>{_OWNER})/(?P<repo>{_REPO})#(?P<number>{_NUMBER})$")
_URL = re.compile(
    rf"^(?:https?://)?(?:www\.)?github\.com/"
    rf"(?P<owner>{_OWNER})/(?P<repo>{_REPO})/(?:issues|pull)/(?P<number>{_NUMBER})"
    rf"(?:[/?#].*)?$",
    re.IGNORECASE,
)
_CREDENTIALS = re.compile(r"(?:token|access_token|password)=", re.IGNORECASE)


@dataclass(frozen=True)
class IssueRef:
    owner: str
    repo: str
    number: int

    @property
    def short(self) -> str:
        return f"{self.owner}/{self.repo}#{self.number}"

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/issues/{self.number}"

    @property
    def api_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{self.number}"

    @property
    def slug(self) -> str:
        return slugify(f"{self.owner}-{self.repo}-{self.number}")


@dataclass(frozen=True)
class Issue:
    ref: IssueRef
    title: str
    body: str
    state: str
    html_url: str


def parse_issue_ref(value: str) -> IssueRef:
    text = value.strip().rstrip(".,;:")
    if "@" in text or _CREDENTIALS.search(text):
        raise UserError(
            "Issue reference must not include credentials. "
            "Use OWNER/REPO#N or a github.com issue URL."
        )
    if not text:
        raise UserError(
            "Not a GitHub issue. Use OWNER/REPO#N or "
            "https://github.com/OWNER/REPO/issues/N."
        )
    match = _SHORT.match(text) or _URL.match(text)
    if match is None or match.group("repo") in {".", ".."}:
        raise UserError(
            "Not a GitHub issue. Use OWNER/REPO#N or "
            "https://github.com/OWNER/REPO/issues/N."
        )
    return IssueRef(match.group("owner"), match.group("repo"), int(match.group("number")))


def github_token() -> str | None:
    chosen: tuple[str, str] | None = None
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name)
        if value:
            chosen = (name, value)
            break
    if chosen is None:
        return None
    name, value = chosen
    if any(char.isspace() for char in value):
        raise FetchError(f"{name} contains whitespace. Refusing to send it.")
    return value


def fetch_issue(ref: IssueRef) -> Issue:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"issue-repro/{__version__}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(ref.api_url, headers=headers)
    try:
        with urlopen(request, timeout=FETCH_TIMEOUT) as response:
            final_url = response.geturl()
            if not str(final_url).startswith("https://api.github.com/"):
                raise FetchError(
                    f"GitHub API redirected away from api.github.com for {ref.short}."
                )
            raw = response.read(_MAX_BYTES + 1)
    except HTTPError as exc:
        raise FetchError(_http_error_message(ref, exc)) from exc
    except FetchError:
        raise
    except (URLError, TimeoutError, OSError) as exc:
        reason = scrub_secrets(" ".join(str(exc).split()))
        raise FetchError(f"Could not reach the GitHub API for {ref.short}: {reason}") from exc

    if len(raw) > _MAX_BYTES:
        raise FetchError(f"GitHub API response for {ref.short} was larger than 2 MB.")
    return _parse_issue(ref, raw)


def _http_error_message(ref: IssueRef, exc: HTTPError) -> str:
    detail = _api_message(exc)
    message = f"GitHub API returned HTTP {exc.code} for {ref.short}"
    if detail:
        message = f"{message}: {detail}"
    remaining = ""
    if exc.headers is not None:
        remaining = str(exc.headers.get("X-RateLimit-Remaining") or "")
    if exc.code == 429 or remaining == "0":
        message += ". Rate limit reached; set GITHUB_TOKEN or GH_TOKEN and retry"
    return scrub_secrets(message)


def _api_message(exc: HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    message = payload.get("message")
    if not isinstance(message, str):
        return ""
    flattened = " ".join(scrub_secrets(message).split())
    if len(flattened) > 180:
        return flattened[:177] + "..."
    return flattened


def _parse_issue(ref: IssueRef, raw: bytes) -> Issue:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchError(f"GitHub API returned an unreadable body for {ref.short}.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("title"), str):
        raise FetchError(f"GitHub API returned an unexpected issue payload for {ref.short}.")

    title = " ".join(scrub_secrets(payload["title"]).split())
    body_value = payload.get("body")
    if isinstance(body_value, str):
        body = scrub_secrets(body_value).replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    else:
        body = ""

    state_value = payload.get("state")
    state = " ".join(scrub_secrets(state_value).split()) if isinstance(state_value, str) else ""
    if len(state) > 40:
        state = ""

    html_url = payload.get("html_url")
    if (
        isinstance(html_url, str)
        and html_url.startswith("https://github.com/")
        and " " not in html_url
    ):
        html_url = scrub_secrets(html_url)
    else:
        html_url = ref.html_url

    return Issue(ref=ref, title=title, body=body, state=state, html_url=html_url)
