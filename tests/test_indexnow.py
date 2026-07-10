"""Tests for etl/indexnow.py — the IndexNow ping that POSTs the sitemap URL list
to api.indexnow.org after each deploy (Bing/Yandex/Seznam fast-index).

Investor-grade discipline: NO network. main() does HTTP via indexnow.fetch and
urllib.request.urlopen; both are monkeypatched to canned values. The pure
sitemap-index parser is unit-tested offline with no fetch at all.

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


def _urlset(urls):
    """Build a minimal sitemap urlset wrapping each url in <url><loc>…</loc></url>."""
    locs = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>'


def _sitemap_index(child_urls):
    """Build a minimal sitemap-index listing child sitemap URLs."""
    locs = "".join(f"<sitemap><loc>{u}</loc></sitemap>" for u in child_urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{locs}</sitemapindex>"
    )


# ---------------------------------------------------------------------------
# Offline pure parser: sitemap-index → child sitemaps → page URLs
# ---------------------------------------------------------------------------
def test_extract_locs_from_urlset():
    urls = ["https://evidaxis.org/", "https://evidaxis.org/about/"]
    assert indexnow.extract_locs(_urlset(urls)) == urls


def test_is_sitemap_index_detects_index_vs_urlset():
    assert indexnow.is_sitemap_index(_sitemap_index(["https://evidaxis.org/sitemap-0.xml"])) is True
    assert indexnow.is_sitemap_index(_urlset(["https://evidaxis.org/"])) is False


def test_collect_urls_from_sitemaps_walks_all_children():
    """Parser expands every child sitemap listed in the index (no sitemap-0 hardcode)."""
    child_a = "https://evidaxis.org/sitemap-0.xml"
    child_b = "https://evidaxis.org/sitemap-1.xml"
    index_xml = _sitemap_index([child_a, child_b])
    child_xml = {
        child_a: _urlset(["https://evidaxis.org/", "https://evidaxis.org/about/"]),
        child_b: _urlset(["https://evidaxis.org/snapshots/", "https://evidaxis.org/snapshots/2026-07-10/"]),
    }
    got = indexnow.collect_urls_from_sitemaps(index_xml, child_xml)
    assert got == [
        "https://evidaxis.org/",
        "https://evidaxis.org/about/",
        "https://evidaxis.org/snapshots/",
        "https://evidaxis.org/snapshots/2026-07-10/",
    ]


def test_collect_urls_from_sitemaps_bare_urlset_fallback():
    """If the index URL returns a urlset directly, treat its <loc>s as page URLs."""
    urls = ["https://evidaxis.org/x", "https://evidaxis.org/y"]
    assert indexnow.collect_urls_from_sitemaps(_urlset(urls), {}) == urls


def test_collect_url_list_appends_llms_txt(monkeypatch):
    """Submitted list always includes /llms.txt even when the sitemap omits it."""
    child = "https://evidaxis.org/sitemap-0.xml"
    pages = ["https://evidaxis.org/", "https://evidaxis.org/about/"]
    bodies = {
        indexnow.SITEMAP_INDEX: _sitemap_index([child]),
        child: _urlset(pages),
    }
    monkeypatch.setattr(indexnow, "fetch", lambda url: bodies[url])
    got = indexnow.collect_url_list()
    assert got[:2] == pages
    assert got[-1] == indexnow.LLMS_TXT
    assert got.count(indexnow.LLMS_TXT) == 1


def test_collect_url_list_does_not_duplicate_llms_txt(monkeypatch):
    child = "https://evidaxis.org/sitemap-0.xml"
    pages = ["https://evidaxis.org/", indexnow.LLMS_TXT]
    bodies = {
        indexnow.SITEMAP_INDEX: _sitemap_index([child]),
        child: _urlset(pages),
    }
    monkeypatch.setattr(indexnow, "fetch", lambda url: bodies[url])
    got = indexnow.collect_url_list()
    assert got.count(indexnow.LLMS_TXT) == 1


# ---------------------------------------------------------------------------
# main(): happy path — parses index+children and POSTs the right JSON payload
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
    child = "https://evidaxis.org/sitemap-0.xml"
    bodies = {
        indexnow.SITEMAP_INDEX: _sitemap_index([child]),
        child: _urlset(urls),
    }
    monkeypatch.setattr(indexnow, "fetch", lambda url: bodies[url])

    def fake_urlopen(req, timeout=30):
        captured["req"] = req
        captured["data"] = req.data
        captured["url"] = req.full_url
        return _FakeResp(status=200)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    indexnow.main()

    assert captured["url"] == "https://api.indexnow.org/indexnow"

    payload = json.loads(captured["data"].decode())
    assert payload["host"] == indexnow.HOST
    assert payload["key"] == indexnow.KEY
    assert payload["keyLocation"] == indexnow.KEY_LOCATION
    # page URLs from sitemaps + mandatory /llms.txt
    assert payload["urlList"] == [*urls, indexnow.LLMS_TXT]

    assert captured["req"].headers["Content-type"] == "application/json; charset=utf-8"

    out = capsys.readouterr().out
    assert f"submitted {len(urls) + 1} URLs" in out
    assert "HTTP 200" in out


def test_main_payload_is_valid_json_bytes(monkeypatch):
    """The POST body must be UTF-8-encoded JSON bytes (urllib requires bytes data)."""
    captured = {}
    child = "https://evidaxis.org/sitemap-0.xml"
    bodies = {
        indexnow.SITEMAP_INDEX: _sitemap_index([child]),
        child: _urlset(["https://evidaxis.org/x"]),
    }
    monkeypatch.setattr(indexnow, "fetch", lambda url: bodies[url])

    def grab(req, timeout=30):
        captured["data"] = req.data
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", grab)
    indexnow.main()
    assert isinstance(captured["data"], (bytes, bytearray))
    json.loads(captured["data"].decode("utf-8"))  # round-trips cleanly


# ---------------------------------------------------------------------------
# empty sitemap: no <loc> → prints 'no URLs' and returns WITHOUT POSTing
# (llms.txt alone is still submitted — empty index with no children yields
# only the mandatory /llms.txt entry, which is a valid non-empty list)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "xml",
    [
        '<?xml version="1.0"?><urlset></urlset>',  # well-formed, zero <loc>
        "",                                          # empty body
        "totally not xml",                           # garbage, still zero <loc>
    ],
)
def test_main_empty_sitemap_still_submits_llms_txt(monkeypatch, capsys, xml):
    """Even with zero sitemap locs, /llms.txt is submitted (explicit IndexNow surface)."""
    captured = {}
    monkeypatch.setattr(indexnow, "fetch", lambda url: xml)

    def grab(req, timeout=30):
        captured["data"] = req.data
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", grab)
    indexnow.main()
    payload = json.loads(captured["data"].decode())
    assert payload["urlList"] == [indexnow.LLMS_TXT]
    assert "submitted 1 URLs" in capsys.readouterr().out


def test_main_empty_after_stripping_does_not_post(monkeypatch, capsys):
    """If collect_url_list somehow returns [], main must not POST."""
    monkeypatch.setattr(indexnow, "collect_url_list", lambda: [])

    def must_not_call(req, timeout=30):
        raise AssertionError("urlopen must NOT be called when there are no URLs")

    monkeypatch.setattr(urllib.request, "urlopen", must_not_call)
    indexnow.main()
    assert "no URLs in sitemap" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# HTTPError path: urlopen raises HTTPError → main() handles it, does not raise.
# ---------------------------------------------------------------------------
def test_urllib_error_is_reachable_via_request_import():
    import urllib  # the bare package

    assert hasattr(urllib, "error"), (
        "indexnow imports only urllib.request; if urllib.error were not reachable, "
        "the `except urllib.error.HTTPError` line in main() would raise AttributeError"
    )
    assert urllib.error.HTTPError is urllib.request.HTTPError  # same class object


@pytest.mark.parametrize("code,reason", [(403, "Forbidden"), (429, "Too Many Requests"), (500, "Server Error")])
def test_main_handles_httperror_without_raising(monkeypatch, capsys, code, reason):
    child = "https://evidaxis.org/sitemap-0.xml"
    bodies = {
        indexnow.SITEMAP_INDEX: _sitemap_index([child]),
        child: _urlset(["https://evidaxis.org/", "https://evidaxis.org/about"]),
    }
    monkeypatch.setattr(indexnow, "fetch", lambda url: bodies[url])

    def raise_http(req, timeout=30):
        raise urllib.error.HTTPError(
            "https://api.indexnow.org/indexnow", code, reason, hdrs={}, fp=None
        )

    monkeypatch.setattr(urllib.request, "urlopen", raise_http)

    indexnow.main()

    out = capsys.readouterr().out
    assert f"HTTP {code}" in out
    assert reason in out
    # 2 page URLs + llms.txt
    assert "3 URLs" in out


def test_main_does_not_swallow_non_http_errors(monkeypatch):
    """The except clause is narrow (HTTPError only): a generic transport failure
    such as URLError must still propagate, not be silently swallowed."""
    child = "https://evidaxis.org/sitemap-0.xml"
    bodies = {
        indexnow.SITEMAP_INDEX: _sitemap_index([child]),
        child: _urlset(["https://evidaxis.org/"]),
    }
    monkeypatch.setattr(indexnow, "fetch", lambda url: bodies[url])

    def raise_urlerror(req, timeout=30):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", raise_urlerror)

    with pytest.raises(urllib.error.URLError):
        indexnow.main()


# ---------------------------------------------------------------------------
# fetch(): the network primitive. Monkeypatch urlopen so no real request fires.
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

    body = indexnow.fetch("https://evidaxis.org/sitemap-index.xml")

    assert body == "héllo"
    assert seen["url"] == "https://evidaxis.org/sitemap-index.xml"
    assert seen["ua"] == "evidaxis-indexnow/1"
    assert seen["timeout"] == 30


# ---------------------------------------------------------------------------
# module-level constants: stable, internally consistent — and the PUBLIC key note
# ---------------------------------------------------------------------------
def test_constants_are_consistent():
    assert indexnow.HOST == "evidaxis.org"
    assert indexnow.SITEMAP_INDEX == f"https://{indexnow.HOST}/sitemap-index.xml"
    assert indexnow.SITEMAP == indexnow.SITEMAP_INDEX  # back-compat alias
    assert indexnow.LLMS_TXT == f"https://{indexnow.HOST}/llms.txt"
    assert indexnow.KEY_LOCATION == f"https://{indexnow.HOST}/{indexnow.KEY}.txt"
    # Kill the old sitemap-0 hardcode
    assert "sitemap-0" not in indexnow.SITEMAP_INDEX


def test_key_is_public_by_design():
    """indexnow.KEY is a PUBLIC IndexNow verification key, NOT a leaked secret.

    The IndexNow spec REQUIRES the key to be served in cleartext at KEY_LOCATION so
    the search engine can fetch it and verify domain ownership. It is also sent in
    the POST payload (key=…) on every ping. Hard-coding and asserting on it here is
    correct and safe — it is meant to be world-readable at the published URL.
    """
    assert indexnow.KEY == "be23b52b58b549cfa47bac03cb09819c"
    assert 8 <= len(indexnow.KEY) <= 128
    assert indexnow.KEY in indexnow.KEY_LOCATION
