"""openalex_keyed_fetch: URL rewriting, 409 hard-fail, non-OpenAlex passthrough.

HARD: no network. The urllib chokepoint is monkeypatched, same discipline as
test_archive_pin.py / test_collect_http.py.
"""
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import openalex_keyed_fetch as okf


def test_rewrite_strips_mailto_and_appends_key():
    url = "https://api.openalex.org/works/W1?select=id&mailto=research@evidaxis.org"
    out = okf._rewrite(url, "K123")
    assert "mailto" not in out
    assert out.endswith("&api_key=K123")
    assert out.startswith("https://api.openalex.org/works/W1?select=id")


def test_rewrite_handles_no_query():
    assert okf._rewrite("https://api.openalex.org/works/W1", "K") == \
        "https://api.openalex.org/works/W1?api_key=K"


def test_non_openalex_url_delegates_to_frozen_fetcher(monkeypatch):
    calls = {}

    def fake_orig(url, headers=None, tries=5):
        calls["url"] = url
        return {"ok": 1}

    monkeypatch.setattr(okf, "_ORIG_GET_JSON", fake_orig)
    out = okf._get_json_keyed("https://api.github.com/repos/x/y")
    assert out == {"ok": 1}
    assert calls["url"] == "https://api.github.com/repos/x/y"


class _Resp:
    def __init__(self, body):
        self._body = body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self):
        return json.dumps(self._body).encode()


def test_keyed_fetch_rewrites_and_returns_json(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "SECRET")
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        return _Resp({"id": "W1"})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = okf._get_json_keyed("https://api.openalex.org/works/W1?select=id&mailto=x@y.z")
    assert out == {"id": "W1"}
    assert "mailto" not in seen["url"]
    assert "api_key=SECRET" in seen["url"]


def test_409_hard_fails_instead_of_silent_absent(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "SECRET")

    def fake_urlopen(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 409, "conflict", None, io.BytesIO(b""))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(SystemExit) as exc:
        okf._get_json_keyed("https://api.openalex.org/works/W1")
    assert exc.value.code == 3


def test_keyless_keeps_url_untouched(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.setattr(okf, "_load_key", lambda: "")
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        return _Resp({})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    okf._get_json_keyed("https://api.openalex.org/works/W1?mailto=a@b.c")
    assert seen["url"] == "https://api.openalex.org/works/W1?mailto=a@b.c"
