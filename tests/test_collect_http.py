"""HTTP + token-loading unit tests for etl/collect.py.

Scope: collect._get_json (the stdlib urllib retry wrapper) and
collect._load_github_token (env / .env / EVIDAXIS_GITHUB_ENV resolution).

NO NETWORK: urllib.request.urlopen is monkeypatched to a fake that yields a
context-manager response (.status + .read()) or raises urllib.error.HTTPError;
time.sleep is patched to a no-op so retry loops run instantly. Token tests
redirect collect.ROOT to tmp and write a throwaway .env there — the real repo
tree is never read or mutated. We test the FUNCTION _load_github_token(), not
the module-level GH_TOKEN (which was bound once at import time).
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

import collect


# ---------------------------------------------------------------- fakes


class _FakeResp:
    """Minimal urlopen() return: context manager exposing .status + .read()."""

    def __init__(self, status=200, payload=None):
        self.status = status
        self._body = json.dumps(payload if payload is not None else {}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def _httperror(code):
    """Build a urllib.error.HTTPError with the given .code (fp must be readable)."""
    return urllib.error.HTTPError(
        url="http://x", code=code, msg="x", hdrs=None, fp=io.BytesIO(b"")
    )


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Retry loops sleep on 202/500/exception — neutralize so tests are instant."""
    monkeypatch.setattr(collect.time, "sleep", lambda *_a, **_k: None)


def _patch_urlopen(monkeypatch, side_effects):
    """side_effects: list consumed one per call; each item is either a _FakeResp
    (returned) or an Exception instance (raised). Records the call count."""
    calls = {"n": 0}
    seq = list(side_effects)

    def fake(req, timeout=None):
        i = calls["n"]
        calls["n"] += 1
        item = seq[i] if i < len(seq) else seq[-1]
        if isinstance(item, BaseException):
            raise item
        return item

    monkeypatch.setattr(collect.urllib.request, "urlopen", fake)
    return calls


# ---------------------------------------------------------------- _get_json: happy path


def test_get_json_200_returns_parsed_dict(monkeypatch):
    _patch_urlopen(monkeypatch, [_FakeResp(200, {"hello": "world", "n": 7})])
    out = collect._get_json("http://api/x", headers={"User-Agent": "t"}, tries=2)
    assert out == {"hello": "world", "n": 7}


def test_get_json_default_headers_used(monkeypatch):
    """headers=None branch: a default UA dict is constructed (no crash, parses)."""
    seen = {}

    def fake(req, timeout=None):
        seen["ua"] = req.get_header("User-agent")
        return _FakeResp(200, {"ok": True})

    monkeypatch.setattr(collect.urllib.request, "urlopen", fake)
    out = collect._get_json("http://api/y")  # headers omitted, default tries
    assert out == {"ok": True}
    assert seen["ua"] == "evidaxis-collect/2.0"


# ---------------------------------------------------------------- _get_json: 202 retry


def test_get_json_202_then_200_retries(monkeypatch):
    """status 202 (GitHub computing stats) -> sleep+continue, then 200 succeeds."""
    calls = _patch_urlopen(monkeypatch, [_FakeResp(202), _FakeResp(200, {"v": 1})])
    out = collect._get_json("http://api/z", tries=2)
    assert out == {"v": 1}
    assert calls["n"] == 2  # both iterations consumed


def test_get_json_all_202_exhausts_to_none(monkeypatch):
    """Every iteration is 202 -> loop runs `tries` times then falls through to None."""
    calls = _patch_urlopen(monkeypatch, [_FakeResp(202), _FakeResp(202)])
    out = collect._get_json("http://api/z", tries=2)
    assert out is None
    assert calls["n"] == 2


def test_get_json_httperror_202_then_success(monkeypatch):
    """HTTPError path with code 202 also retries (mirrors the success-status 202)."""
    calls = _patch_urlopen(monkeypatch, [_httperror(202), _FakeResp(200, {"a": "b"})])
    out = collect._get_json("http://api/z", tries=2)
    assert out == {"a": "b"}
    assert calls["n"] == 2


# ---------------------------------------------------------------- _get_json: rate limit / 404


@pytest.mark.parametrize("code", [403, 429])
def test_get_json_ratelimit_codes_return_sentinel(monkeypatch, code):
    """403 / 429 -> immediate 'RATELIMIT' sentinel (no retry, caller aborts)."""
    calls = _patch_urlopen(monkeypatch, [_httperror(code)])
    out = collect._get_json("http://api/limited", tries=2)
    assert out == "RATELIMIT"
    assert calls["n"] == 1  # returned on first error, no retry


def test_get_json_404_returns_none(monkeypatch):
    """404 -> None immediately (entity simply has no data; not an error to retry)."""
    calls = _patch_urlopen(monkeypatch, [_httperror(404)])
    out = collect._get_json("http://api/missing", tries=2)
    assert out is None
    assert calls["n"] == 1


# ---------------------------------------------------------------- _get_json: 500 / generic retry-to-None


def test_get_json_500_retries_then_none(monkeypatch):
    """5xx -> sleep+continue each time; after `tries` attempts returns None."""
    calls = _patch_urlopen(monkeypatch, [_httperror(500), _httperror(500)])
    out = collect._get_json("http://api/boom", tries=2)
    assert out is None
    assert calls["n"] == 2  # retried the full budget


def test_get_json_500_then_success(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [_httperror(500), _FakeResp(200, {"ok": 1})])
    out = collect._get_json("http://api/boom", tries=2)
    assert out == {"ok": 1}
    assert calls["n"] == 2


def test_get_json_generic_exception_retries_then_none(monkeypatch):
    """A non-HTTPError (e.g. URLError/timeout) -> caught, retried, then None."""
    calls = _patch_urlopen(monkeypatch, [ValueError("boom"), RuntimeError("again")])
    out = collect._get_json("http://api/flaky", tries=2)
    assert out is None
    assert calls["n"] == 2


def test_get_json_generic_exception_then_success(monkeypatch):
    calls = _patch_urlopen(monkeypatch, [TimeoutError("slow"), _FakeResp(200, {"r": 9})])
    out = collect._get_json("http://api/flaky", tries=2)
    assert out == {"r": 9}
    assert calls["n"] == 2


def test_get_json_tries_one_single_attempt(monkeypatch):
    """tries=1 with a transient 500 gives exactly one attempt then None."""
    calls = _patch_urlopen(monkeypatch, [_httperror(500)])
    out = collect._get_json("http://api/x", tries=1)
    assert out is None
    assert calls["n"] == 1


# ---------------------------------------------------------------- _load_github_token


def test_load_token_from_env(monkeypatch):
    """GITHUB_TOKEN set in env -> returned, stripped of surrounding whitespace."""
    monkeypatch.setenv("GITHUB_TOKEN", "  ghp_envtoken  ")
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    assert collect._load_github_token() == "ghp_envtoken"


def test_load_token_from_dotenv_quotes_stripped(tmp_path, monkeypatch):
    """Empty env + a .env at ROOT containing GITHUB_TOKEN="abc" -> 'abc' (quotes off)."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    monkeypatch.setattr(collect, "ROOT", tmp_path, raising=True)
    (tmp_path / ".env").write_text(
        "# comment line\nOTHER=ignore\nGITHUB_TOKEN=\"abc\"\n"
    )
    assert collect._load_github_token() == "abc"


def test_load_token_from_dotenv_single_quotes(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    monkeypatch.setattr(collect, "ROOT", tmp_path, raising=True)
    (tmp_path / ".env").write_text("GITHUB_TOKEN='single'\n")
    assert collect._load_github_token() == "single"


def test_load_token_env_takes_precedence_over_dotenv(tmp_path, monkeypatch):
    """env value wins and the .env is never consulted."""
    monkeypatch.setenv("GITHUB_TOKEN", "from_env")
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    monkeypatch.setattr(collect, "ROOT", tmp_path, raising=True)
    (tmp_path / ".env").write_text('GITHUB_TOKEN="from_dotenv"\n')
    assert collect._load_github_token() == "from_env"


def test_load_token_from_evidaxis_github_env_path(tmp_path, monkeypatch):
    """EVIDAXIS_GITHUB_ENV points at a custom file; ROOT/.env absent -> custom used."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    # ROOT/.env must NOT exist, else it is checked first (see ordering test below).
    fake_root = tmp_path / "etl"
    fake_root.mkdir()
    monkeypatch.setattr(collect, "ROOT", fake_root, raising=True)
    custom = tmp_path / "custom.env"
    custom.write_text('GITHUB_TOKEN="from_custom"\n')
    monkeypatch.setenv("EVIDAXIS_GITHUB_ENV", str(custom))
    assert collect._load_github_token() == "from_custom"


def test_load_token_root_dotenv_checked_before_custom_path(tmp_path, monkeypatch):
    """Ordering: the candidate tuple is (ROOT/.env, EVIDAXIS_GITHUB_ENV). When BOTH
    exist, ROOT/.env is consulted first and its token wins."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    fake_root = tmp_path / "etl"
    fake_root.mkdir()
    monkeypatch.setattr(collect, "ROOT", fake_root, raising=True)
    (fake_root / ".env").write_text('GITHUB_TOKEN="root_wins"\n')
    custom = tmp_path / "custom.env"
    custom.write_text('GITHUB_TOKEN="custom_loses"\n')
    monkeypatch.setenv("EVIDAXIS_GITHUB_ENV", str(custom))
    assert collect._load_github_token() == "root_wins"


def test_load_token_nothing_present_returns_empty(tmp_path, monkeypatch):
    """No env var, no .env file anywhere -> ''."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    fake_root = tmp_path / "etl"
    fake_root.mkdir()
    monkeypatch.setattr(collect, "ROOT", fake_root, raising=True)
    assert collect._load_github_token() == ""


def test_load_token_dotenv_without_token_line_returns_empty(tmp_path, monkeypatch):
    """A .env that exists but has no GITHUB_TOKEN= line -> '' (loop finds nothing)."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    monkeypatch.setattr(collect, "ROOT", tmp_path, raising=True)
    (tmp_path / ".env").write_text("FOO=bar\nBAZ=qux\n")
    assert collect._load_github_token() == ""


def test_load_token_unreadable_dotenv_is_swallowed(tmp_path, monkeypatch):
    """A candidate path that .exists() but raises on read (here: it's a directory,
    so read_text -> IsADirectoryError) is caught by the bare except and skipped ->
    falls through to '' rather than propagating."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    fake_root = tmp_path / "etl"
    fake_root.mkdir()
    monkeypatch.setattr(collect, "ROOT", fake_root, raising=True)
    # ROOT/.env is itself a directory: .exists() True, .read_text() raises.
    (fake_root / ".env").mkdir()
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    assert collect._load_github_token() == ""


def test_load_token_empty_env_value_falls_through_to_dotenv(tmp_path, monkeypatch):
    """GITHUB_TOKEN='' (whitespace-only) is falsy after strip -> falls through to .env."""
    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    monkeypatch.setattr(collect, "ROOT", tmp_path, raising=True)
    (tmp_path / ".env").write_text('GITHUB_TOKEN="recovered"\n')
    assert collect._load_github_token() == "recovered"
