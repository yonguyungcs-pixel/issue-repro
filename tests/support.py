"""HTTP stand-ins for GitHub API tests."""

from __future__ import annotations

import io
import json
from email.message import Message
from urllib.error import HTTPError


class Response:
    def __init__(self, payload, url="https://api.github.com/repos/acme/widgets/issues/5"):
        if isinstance(payload, bytes):
            self._data = payload
        else:
            self._data = json.dumps(payload).encode()
        self._url = url

    def read(self, limit=-1):
        if limit is None or limit < 0:
            data, self._data = self._data, b""
            return data
        data, self._data = self._data[:limit], self._data[limit:]
        return data

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def http_error(code, body=b"", headers=None):
    return HTTPError(
        url="https://api.github.com/repos/acme/widgets/issues/5",
        code=code,
        msg="error",
        hdrs=headers if headers is not None else Message(),
        fp=io.BytesIO(body),
    )
