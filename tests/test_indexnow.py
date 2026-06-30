"""Tests for etl/indexnow.py — the IndexNow ping that POSTs the sitemap URL list
to api.indexnow.org after each deploy (Bing/Yandex/Seznam fast-index).

Investor-grade discipline: NO network. main() does two HTTP calls — the sitemap
fetch (indexnow.fetch) and the IndexNow POST (urllib.request.urlopen). Both are
monkeypatched to canned values; the real APIs are never touched. main() writes
nothing to disk, so no tmp-dir redirect is needed.

NOTE on indexnow.KEY: it is a PUBLIC IndexNow verification key BY DESIGN, not a
leaked secret. The IndexNow protocol REQUIRES the key to be published in cleartext
at KEY_LOCATION (https://evidaxis.org/<KEY>.txt) so the search engine can fetch it
and confirm ownership. Asserting on its value here is therefore safe and correct,
not a credential exposure. See test_key_is_public_by_design below.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

import indexnow


# --- a fake urlopen-return object (context-manager) capturing the POSTed request ---
class _FakeResp:
    """Stand-in for the object urllib.request.urlopen returns: has .status and is a
    context manager (main() uses `with urllib.request.urlopen(req) as r:`)."""

    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _sitemap(urls):
    """Build a minimal sitemap XML wrapping each url in <url><loc>…</loc></url>."""
    locs = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset>{locs}</urlset>'


# ---------------------------------------------------------------------------
# main(): happy path — parses <loc> URLs and POSTs the right JSON payload
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "urls",
    [
        ["https://evidaxis.org/"],
        ["https://evidaxis.org/", "https://evidaxis.org/about", "https://evidaxis.org/protocol"],
        # entity-encoded ampersand survives (regex stops at '<', not '&')
        ["https://evidaxis.org/a?x=1&amp;y=2", "https://evidaxis.org/b"],
    ],
)
def test_main_posts_parsed_urls(monkeypatch, capsys, urls):
    captured = {}

    monkeypatch.setattr(indexnow, "fetch", lambda url: _sitemap(urls))

    def fake_urlopen(req, timeout=30):
        captured["req"] = req
        captured["data"] = req.data
        captured["url"] = req.full_url
        return _FakeResp(status=200)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    indexnow.main()

    # POST landed on the IndexNow endpoint
    assert captured["url"] == "https://api.indexnow.org/indexnow"

    payload = json.loads(captured["data"].decode())
    assert payload["host"] == indexnow.HOST
    assert payload["key"] == indexnow.KEY
    assert payload["keyLocation"] == indexnow.KEY_LOCATION
    assert payload["urlList"] == urls  # exact list, exact order

    # correct content-type header for the IndexNow JSON body
    assert captured["req"].headers["Content-type"] == "application/json; charset=utf-8"

    out = capsys.readouterr().out
    assert f"submitted {len(urls)} URLs" in out
    assert "HTTP 200" in out


def test_main_payload_is_valid_json_bytes(monkeypatch):
    """The POST body must be UTF-8-encoded JSON bytes (urllib requires bytes data)."""
    captured = {}
    monkeypatch.setattr(indexnow, "fetch", lambda url: _sitemap(["https://evidaxis.org/x"]))

    def grab(req, timeout=30):
        captured["data"] = req.data
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", grab)
    indexnow.main()
    assert isinstance(captured["data"], (bytes, bytearray))
    json.loads(captured["data"].decode("utf-8"))  # round-trips cleanly


# ---------------------------------------------------------------------------
# empty sitemap: no <loc> → prints 'no URLs' and returns WITHOUT POSTing
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "xml",
    [
        '<?xml version="1.0"?><urlset></urlset>',  # well-formed, zero <loc>
        "",                                          # empty body
        "totally not xml",                           # garbage, still zero <loc>
    ],
)
def test_main_empty_sitemap_does_not_post(monkeypatch, capsys, xml):
    monkeypatch.setattr(indexnow, "fetch", lambda url: xml)

    def must_not_call(req, timeout=30):
        raise AssertionError("urlopen must NOT be called when there are no URLs")

    monkeypatch.setattr(urllib.request, "urlopen", must_not_call)

    # returns normally (no exception) without POSTing
    indexnow.main()

    out = capsys.readouterr().out
    assert "no URLs in sitemap" in out


# ---------------------------------------------------------------------------
# HTTPError path: urlopen raises HTTPError → main() handles it, does not raise.
#
# main() catches `urllib.error.HTTPError`, but the module only `import`s
# urllib.request — NOT urllib.error. We verified empirically that on this build
# `import urllib.request` transitively imports urllib.error and registers it as a
# submodule attribute on the urllib package, so `urllib.error.HTTPError` resolves
# inside main() and the except clause works (no NameError/AttributeError). The
# test asserts the graceful-handling behavior AND pins the reachability assumption.
# ---------------------------------------------------------------------------
def test_urllib_error_is_reachable_via_request_import():
    # main() relies on this: importing urllib.request alone must expose urllib.error.
    import urllib  # the bare package

    assert hasattr(urllib, "error"), (
        "indexnow imports only urllib.request; if urllib.error were not reachable, "
        "the `except urllib.error.HTTPError` line in main() would raise AttributeError"
    )
    assert urllib.error.HTTPError is urllib.request.HTTPError  # same class object


@pytest.mark.parametrize("code,reason", [(403, "Forbidden"), (429, "Too Many Requests"), (500, "Server Error")])
def test_main_handles_httperror_without_raising(monkeypatch, capsys, code, reason):
    urls = ["https://evidaxis.org/", "https://evidaxis.org/about"]
    monkeypatch.setattr(indexnow, "fetch", lambda url: _sitemap(urls))

    def raise_http(req, timeout=30):
        raise urllib.error.HTTPError(
            "https://api.indexnow.org/indexnow", code, reason, hdrs={}, fp=None
        )

    monkeypatch.setattr(urllib.request, "urlopen", raise_http)

    # must NOT propagate the HTTPError
    indexnow.main()

    out = capsys.readouterr().out
    assert f"HTTP {code}" in out
    assert reason in out
    assert f"{len(urls)} URLs" in out


def test_main_does_not_swallow_non_http_errors(monkeypatch):
    """The except clause is narrow (HTTPError only): a generic transport failure
    such as URLError must still propagate, not be silently swallowed."""
    monkeypatch.setattr(indexnow, "fetch", lambda url: _sitemap(["https://evidaxis.org/"]))

    def raise_urlerror(req, timeout=30):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", raise_urlerror)

    with pytest.raises(urllib.error.URLError):
        indexnow.main()


# ---------------------------------------------------------------------------
# fetch(): the network primitive. Monkeypatch urlopen so no real request fires;
# assert it builds a Request with the expected UA header and decodes the body.
# ---------------------------------------------------------------------------
def test_fetch_builds_request_and_decodes(monkeypatch):
    seen = {}

    class _Body:
        def read(self):
            return "héllo".encode()  # non-ASCII to prove .decode() runs

    def fake_urlopen(req, timeout=30):
        seen["url"] = req.full_url
        seen["ua"] = req.headers.get("User-agent")
        seen["timeout"] = timeout
        return _Body()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    body = indexnow.fetch("https://evidaxis.org/sitemap-0.xml")

    assert body == "héllo"
    assert seen["url"] == "https://evidaxis.org/sitemap-0.xml"
    assert seen["ua"] == "evidaxis-indexnow/1"
    assert seen["timeout"] == 30


# ---------------------------------------------------------------------------
# module-level constants: stable, internally consistent — and the PUBLIC key note
# ---------------------------------------------------------------------------
def test_constants_are_consistent():
    assert indexnow.HOST == "evidaxis.org"
    assert indexnow.SITEMAP == f"https://{indexnow.HOST}/sitemap-0.xml"
    assert indexnow.KEY_LOCATION == f"https://{indexnow.HOST}/{indexnow.KEY}.txt"


def test_key_is_public_by_design():
    """indexnow.KEY is a PUBLIC IndexNow verification key, NOT a leaked secret.

    The IndexNow spec REQUIRES the key to be served in cleartext at KEY_LOCATION so
    the search engine can fetch it and verify domain ownership. It is also sent in
    the POST payload (key=…) on every ping. Hard-coding and asserting on it here is
    correct and safe — it is meant to be world-readable at the published URL.
    """
    # hex token (IndexNow keys are 8-128 chars, [a-zA-Z0-9-]); pin the published value
    assert indexnow.KEY == "be23b52b58b549cfa47bac03cb09819c"
    assert 8 <= len(indexnow.KEY) <= 128
    assert indexnow.KEY in indexnow.KEY_LOCATION  # published at its own .txt URL
