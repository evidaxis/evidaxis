"""Tests for etl/archive_pin.py — pins each genesis source pre-image to Wayback +
Software Heritage and writes data/snapshots/<date>/archive-pointers.json.

HARD: no network. Every HTTP path is exercised by monkeypatching archive_pin._req
(the single stdlib-urllib chokepoint) to return canned (status, final_url, body)
triples. The only artifact-writing test (main) redirects archive_pin.SNAP to a tmp
dir, so the real repo tree is never touched. time.sleep is stubbed to a no-op so the
two conservative throttle sleeps (5s + 6s per repo) don't slow the suite.
"""
import json

import pytest

import archive_pin


# ---------------------------------------------------------------------------
# _req — the urllib chokepoint. We don't hit the network; we only assert that it
# builds the Request correctly and unpacks the three error/success branches by
# monkeypatching urllib.request.urlopen + the HTTPError/exception types.
# ---------------------------------------------------------------------------
class _FakeResp:
    """Context-manager stand-in for the urlopen() object."""
    def __init__(self, status, geturl, body):
        self._status = status
        self._geturl = geturl
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def status(self):
        return self._status

    def geturl(self):
        return self._geturl

    def read(self, n=None):
        # archive_pin reads at most 2000 bytes then decodes utf-8
        b = self._body if isinstance(self._body, (bytes, bytearray)) else self._body.encode("utf-8")
        return b[:n] if n is not None else b


def test_req_success_unpacks_status_url_body(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["ua"] = req.headers.get("User-agent")
        captured["timeout"] = timeout
        return _FakeResp(200, "https://web.archive.org/web/2026/x", "hello-body")

    monkeypatch.setattr(archive_pin.urllib.request, "urlopen", fake_urlopen)
    st, final, body = archive_pin._req("https://example.com/x", method="POST", timeout=12)
    assert st == 200
    assert final == "https://web.archive.org/web/2026/x"
    assert body == "hello-body"
    # request was constructed with the right method, url, UA header, timeout
    assert captured["method"] == "POST"
    assert captured["url"] == "https://example.com/x"
    assert captured["ua"] == archive_pin.UA
    assert captured["timeout"] == 12


def test_req_http_error_returns_code_url_and_message(monkeypatch):
    err = archive_pin.urllib.error.HTTPError(
        url="https://example.com/y", code=429, msg="Too Many Requests", hdrs=None, fp=None
    )

    def fake_urlopen(req, timeout=None):
        raise err

    monkeypatch.setattr(archive_pin.urllib.request, "urlopen", fake_urlopen)
    st, final, body = archive_pin._req("https://example.com/y")
    assert st == 429
    # on HTTPError the function echoes back the *passed* url, not resp.geturl()
    assert final == "https://example.com/y"
    assert isinstance(body, str)


def test_req_generic_exception_returns_none_status(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise TimeoutError("boom")

    monkeypatch.setattr(archive_pin.urllib.request, "urlopen", fake_urlopen)
    st, final, body = archive_pin._req("https://example.com/z")
    assert st is None
    assert final == "https://example.com/z"
    assert body.startswith("TimeoutError: ")


# ---------------------------------------------------------------------------
# wayback() — three outcomes: fresh SPN ok, fall back to existing snapshot, both fail.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("spn_status", [200, 301, 302])
def test_wayback_save_page_now_ok(monkeypatch, spn_status):
    final = "https://web.archive.org/web/2026/https://github.com/a/b"

    def fake_req(url, method="GET", timeout=45):
        # first (and only) call is the Save-Page-Now GET
        assert url == "https://web.archive.org/save/https://github.com/a/b"
        return spn_status, final, "saved"

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.wayback("https://github.com/a/b")
    assert out == {"status": "ok", "archived_url": final}


def test_wayback_spn_200_but_no_web_marker_falls_through(monkeypatch):
    # status is 200 but final URL lacks "web.archive.org/web/" → not treated as ok;
    # falls through to availability API (which here reports an existing snapshot).
    calls = []
    existing = "https://web.archive.org/web/2025/https://github.com/a/b"

    def fake_req(url, method="GET", timeout=45):
        calls.append(url)
        if url.startswith("https://web.archive.org/save/"):
            return 200, "https://example.com/not-a-snapshot", "x"
        # availability API
        body = json.dumps({"archived_snapshots": {"closest": {"available": True, "url": existing}}})
        return 200, url, body

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.wayback("https://github.com/a/b")
    assert out == {"status": "existing", "archived_url": existing}
    assert len(calls) == 2  # SPN + availability


def test_wayback_spn_fails_falls_back_to_existing_snapshot(monkeypatch):
    existing = "https://web.archive.org/web/2024/https://github.com/c/d"

    def fake_req(url, method="GET", timeout=45):
        if url.startswith("https://web.archive.org/save/"):
            return 503, url, "service unavailable"
        assert url == "https://archive.org/wayback/available?url=https://github.com/c/d"
        body = json.dumps({"archived_snapshots": {"closest": {"available": True, "url": existing}}})
        return 200, url, body

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.wayback("https://github.com/c/d")
    assert out == {"status": "existing", "archived_url": existing}


def test_wayback_both_fail_returns_failed_with_http(monkeypatch):
    def fake_req(url, method="GET", timeout=45):
        if url.startswith("https://web.archive.org/save/"):
            return 500, url, "err"
        # availability API returns 200 but no available snapshot
        return 200, url, json.dumps({"archived_snapshots": {}})

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.wayback("https://github.com/e/f")
    # "http" carries the SPN status (st), regardless of the availability result
    assert out == {"status": "failed", "http": 500}


def test_wayback_availability_not_available_returns_failed(monkeypatch):
    # availability API explicitly reports available=False → no snapshot → failed
    def fake_req(url, method="GET", timeout=45):
        if url.startswith("https://web.archive.org/save/"):
            return None, url, "TimeoutError: x"
        return 200, url, json.dumps(
            {"archived_snapshots": {"closest": {"available": False, "url": "ignored"}}}
        )

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.wayback("https://github.com/g/h")
    assert out == {"status": "failed", "http": None}


def test_wayback_availability_bad_json_swallowed_returns_failed(monkeypatch):
    # availability API 200 but body is not valid JSON → except: pass → failed
    def fake_req(url, method="GET", timeout=45):
        if url.startswith("https://web.archive.org/save/"):
            return 404, url, "nope"
        return 200, url, "<<<not json>>>"

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.wayback("https://github.com/i/j")
    assert out == {"status": "failed", "http": 404}


def test_wayback_availability_non_200_returns_failed(monkeypatch):
    # availability API itself non-200 → skip JSON parse entirely → failed
    def fake_req(url, method="GET", timeout=45):
        if url.startswith("https://web.archive.org/save/"):
            return 500, url, "err"
        return 429, url, "rate limited"

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.wayback("https://github.com/k/l")
    assert out == {"status": "failed", "http": 500}


# ---------------------------------------------------------------------------
# swh() — POST to Save-Code-Now. Three outcomes: 200+json, 201+non-json, failure.
# ---------------------------------------------------------------------------
def test_swh_200_json_extracts_status_fields(monkeypatch):
    body = json.dumps({
        "save_request_status": "accepted",
        "save_task_status": "scheduled",
        "origin_url": "https://github.com/a/b",
        "extra": "ignored",
    })

    def fake_req(url, method="GET", timeout=45):
        assert method == "POST"
        assert url == "https://archive.softwareheritage.org/api/1/origin/save/git/url/https://github.com/a/b/"
        return 200, url, body

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.swh("https://github.com/a/b")
    assert out == {
        "status": "ok",
        "save_request_status": "accepted",
        "save_task_status": "scheduled",
        "origin_url": "https://github.com/a/b",
    }


def test_swh_201_non_json_returns_raw(monkeypatch):
    raw = "Created — not json " + ("z" * 500)

    def fake_req(url, method="GET", timeout=45):
        assert method == "POST"
        return 201, url, raw

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.swh("https://github.com/c/d")
    assert out["status"] == "ok"
    assert out["raw"] == raw[:200]
    assert len(out["raw"]) == 200
    assert "save_request_status" not in out


def test_swh_200_json_missing_keys_yields_none_values(monkeypatch):
    # valid JSON object but without the expected keys → fields present but None
    def fake_req(url, method="GET", timeout=45):
        return 200, url, json.dumps({"unrelated": 1})

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.swh("https://github.com/e/f")
    assert out == {
        "status": "ok",
        "save_request_status": None,
        "save_task_status": None,
        "origin_url": None,
    }


@pytest.mark.parametrize("status", [400, 404, 429, 500, 503, None])
def test_swh_failure_codes(monkeypatch, status):
    def fake_req(url, method="GET", timeout=45):
        return status, url, "error body"

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    out = archive_pin.swh("https://github.com/g/h")
    assert out == {"status": "failed", "http": status}


# ---------------------------------------------------------------------------
# main() — wires provenance.json -> per-repo wayback+swh -> archive-pointers.json.
# SNAP redirected to a tmp dir; _req canned; time.sleep no-op.
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_snap(tmp_path, monkeypatch):
    snap = tmp_path / "snap"
    snap.mkdir()
    prov = {
        "snapshot_id": "deadbeef99",
        "source_manifest": {"github_repos": ["a/b", "c/d"]},
    }
    (snap / "provenance.json").write_text(json.dumps(prov))
    monkeypatch.setattr(archive_pin, "SNAP", snap, raising=True)
    monkeypatch.setattr(archive_pin.time, "sleep", lambda *a, **k: None)
    return snap


def test_main_writes_pointers_for_each_repo(fake_snap, monkeypatch):
    wb_final = "https://web.archive.org/web/2026/x"

    def fake_req(url, method="GET", timeout=45):
        if url.startswith("https://web.archive.org/save/"):
            return 200, wb_final, "ok"
        if url.startswith("https://archive.softwareheritage.org/"):
            return 200, url, json.dumps({
                "save_request_status": "accepted",
                "save_task_status": "scheduled",
                "origin_url": url,
            })
        # availability API — not reached because SPN succeeds, but be safe
        return 200, url, json.dumps({"archived_snapshots": {}})

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    archive_pin.main()

    out_path = fake_snap / "archive-pointers.json"
    assert out_path.exists()
    out = json.loads(out_path.read_text())

    # top-level policy / provenance fields
    assert out["generated_for_snapshot"] == "deadbeef99"
    assert "Wayback Save-Page-Now" in out["policy"]
    assert "NO IPFS" in out["policy"]

    # one entry per github repo, keyed by repo string
    assert set(out["repos"].keys()) == {"a/b", "c/d"}
    for repo in ("a/b", "c/d"):
        entry = out["repos"][repo]
        assert entry["source_url"] == "https://github.com/" + repo
        assert entry["wayback"] == {"status": "ok", "archived_url": wb_final}
        assert entry["software_heritage"]["status"] == "ok"
        assert entry["software_heritage"]["save_request_status"] == "accepted"


def test_main_mixed_outcomes_persist_per_repo(fake_snap, monkeypatch):
    # a/b: wayback fails entirely + swh fails ; c/d: wayback existing + swh ok
    existing = "https://web.archive.org/web/2020/c/d"

    def fake_req(url, method="GET", timeout=45):
        is_ab = "github.com/a/b" in url
        if url.startswith("https://web.archive.org/save/"):
            return (500, url, "err") if is_ab else (200, "https://example.com/x", "x")
        if url.startswith("https://archive.org/wayback/available"):
            if is_ab:
                return 200, url, json.dumps({"archived_snapshots": {}})
            return 200, url, json.dumps(
                {"archived_snapshots": {"closest": {"available": True, "url": existing}}}
            )
        if url.startswith("https://archive.softwareheritage.org/"):
            return (500, url, "err") if is_ab else (
                201, url, json.dumps({"save_request_status": "pending"})
            )
        raise AssertionError("unexpected url " + url)

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    archive_pin.main()

    out = json.loads((fake_snap / "archive-pointers.json").read_text())
    ab = out["repos"]["a/b"]
    cd = out["repos"]["c/d"]
    assert ab["wayback"] == {"status": "failed", "http": 500}
    assert ab["software_heritage"] == {"status": "failed", "http": 500}
    assert cd["wayback"] == {"status": "existing", "archived_url": existing}
    assert cd["software_heritage"]["status"] == "ok"
    assert cd["software_heritage"]["save_request_status"] == "pending"
    assert cd["software_heritage"]["save_task_status"] is None


def test_main_empty_repo_list_writes_empty_map(tmp_path, monkeypatch):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "provenance.json").write_text(json.dumps(
        {"snapshot_id": "empty01", "source_manifest": {"github_repos": []}}
    ))
    monkeypatch.setattr(archive_pin, "SNAP", snap, raising=True)
    monkeypatch.setattr(archive_pin.time, "sleep", lambda *a, **k: None)

    def fake_req(url, method="GET", timeout=45):
        raise AssertionError("no repos → _req must never be called")

    monkeypatch.setattr(archive_pin, "_req", fake_req)
    archive_pin.main()

    out = json.loads((snap / "archive-pointers.json").read_text())
    assert out["repos"] == {}
    assert out["generated_for_snapshot"] == "empty01"


def test_main_missing_snapshot_id_key_yields_none(fake_snap, monkeypatch):
    # provenance without snapshot_id → prov.get("snapshot_id") is None (uses .get)
    (fake_snap / "provenance.json").write_text(json.dumps(
        {"source_manifest": {"github_repos": []}}
    ))
    monkeypatch.setattr(archive_pin, "_req", lambda *a, **k: (None, "", ""))
    archive_pin.main()
    out = json.loads((fake_snap / "archive-pointers.json").read_text())
    assert out["generated_for_snapshot"] is None
