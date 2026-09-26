"""GitHub fetch layer for the 5,939-system snapshot: App auth, rate-limit waits,
GraphQL batching, warm/capture cache, date pin, owner_classify and t2 routing.

HARD: no network. urllib.request.urlopen, the openssl call and time.sleep are
monkeypatched; the cache lives in tmp_path (never the repo tree).
"""
from __future__ import annotations

import base64
import email.message
import io
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import gh_auth
import gh_graphql
import gh_http
import openalex_keyed_fetch as okf
import owner_classify
import t2_collect


# ---------------------------------------------------------------- helpers


def _msg(headers: dict | None) -> email.message.Message:
    m = email.message.Message()
    for k, v in (headers or {}).items():
        m[k] = str(v)
    return m


class _Resp:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.headers = _msg(headers)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getcode(self):
        return self.status

    def read(self):
        return self._body


class FakeNet:
    """Scripted urlopen: each item is (status, body, headers); status >= 400 raises HTTPError."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def __call__(self, req, timeout=0):
        self.requests.append(req)
        status, body, headers = self.script.pop(0)
        if status >= 400:
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            raise urllib.error.HTTPError(req.full_url, status, "err", _msg(headers), io.BytesIO(raw))
        return _Resp(status, body, headers)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    for var in ("COLLECT_APP_ID", "COLLECT_APP_KEY", "GITHUB_TOKEN", "EVX_PASS", "SNAPSHOT_DATE",
                "EVX_202_WAIT_BUDGET_S"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("EVX_GH_CACHE_DIR", str(tmp_path / "gh-cache"))
    gh_auth.reset(None)
    gh_http.reset_stats()
    okf._reset_run()
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
    yield sleeps
    gh_auth.reset(None)


@pytest.fixture
def sleeps(_isolated):
    return _isolated


def _app_provider(clock, mints_seen=None, installs=None):
    """TokenProvider in app mode with a fake signer and fake App endpoints."""
    counter = {"n": 0}

    def http(method, url, headers, data=None):
        if mints_seen is not None:
            mints_seen.append((method, url, headers["Authorization"]))
        if url.endswith("/app/installations?per_page=100"):
            return 200, json.dumps(installs or [{"id": 7, "account": {"login": "other"}},
                                                {"id": 42, "account": {"login": "Evidaxis"}}]).encode()
        assert url.endswith("/app/installations/42/access_tokens") and method == "POST"
        counter["n"] += 1
        expires = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(clock["t"] + 3600))
        return 201, json.dumps({"token": f"ghs_tok{counter['n']}", "expires_at": expires}).encode()

    env = {"COLLECT_APP_ID": "123", "COLLECT_APP_KEY": "-----BEGIN KEY-----\nx\n-----END KEY-----"}
    return gh_auth.TokenProvider(env=env, now=lambda: clock["t"], http=http,
                                 signer=lambda app_id, key, now=None: "jwt.for.test")


# ---------------------------------------------------------------- gh_auth


def test_jwt_header_claims_and_key_file_hygiene():
    seen = {}

    class Proc:
        returncode = 0
        stdout = b"\x01\x02signature"

    def fake_run(cmd, input=None, capture_output=None, check=None):
        key_path = cmd[-1]
        seen["cmd"] = cmd[:-1]
        seen["mode"] = stat.S_IMODE(os.stat(key_path).st_mode)
        seen["key"] = Path(key_path).read_text()
        seen["path"] = key_path
        seen["input"] = input
        return Proc()

    jwt = gh_auth.make_jwt("123", "-----BEGIN KEY-----\\nabc\\n-----END KEY-----", now=1_000_000, run=fake_run)
    head_b64, claims_b64, sig_b64 = jwt.split(".")

    def dec(part):
        return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))

    assert json.loads(dec(head_b64)) == {"alg": "RS256", "typ": "JWT"}
    assert json.loads(dec(claims_b64)) == {"iat": 1_000_000 - 60, "exp": 1_000_000 + 540, "iss": 123}
    assert dec(sig_b64) == b"\x01\x02signature"
    assert "=" not in jwt
    assert seen["cmd"] == ["openssl", "dgst", "-sha256", "-sign"]
    assert seen["input"] == f"{head_b64}.{claims_b64}".encode()
    assert seen["mode"] == 0o600
    assert seen["key"] == "-----BEGIN KEY-----\nabc\n-----END KEY-----\n"   # escaped newlines restored
    assert not Path(seen["path"]).exists(), "the key file must be deleted after signing"


def test_jwt_signing_failure_never_echoes_key():
    class Proc:
        returncode = 1
        stdout = b""

    with pytest.raises(gh_auth.AuthError) as exc:
        gh_auth.make_jwt("123", "SECRET-PEM-BODY", now=1, run=lambda *a, **k: Proc())
    assert "SECRET-PEM-BODY" not in str(exc.value)


def test_installation_token_cached_and_refreshed_under_ten_minutes():
    clock = {"t": 1_000_000.0}
    calls: list = []
    p = _app_provider(clock, calls)
    assert p.mode == "app"
    assert p.auth_header() == {"Authorization": "Bearer ghs_tok1"}
    assert p.installation_id == 42                           # org match is case-insensitive
    clock["t"] += 49 * 60                                    # 11 min left -> cached
    assert p.token() == "ghs_tok1"
    clock["t"] += 2 * 60                                     # 9 min left -> refresh
    assert p.token() == "ghs_tok2"
    posts = [c for c in calls if c[0] == "POST"]
    gets = [c for c in calls if c[0] == "GET"]
    assert len(posts) == 2 and len(gets) == 1                # installation id looked up once
    assert all(c[2] == "Bearer jwt.for.test" for c in calls)  # App endpoints use the JWT


def test_missing_installation_is_a_loud_error():
    clock = {"t": 0.0}
    p = _app_provider(clock, installs=[{"id": 7, "account": {"login": "someone-else"}}])
    with pytest.raises(gh_auth.AuthError, match="evidaxis"):
        p.token()


def test_fallback_to_github_token_and_anonymous():
    assert gh_auth.TokenProvider(env={"GITHUB_TOKEN": "gt"}).auth_header() == {"Authorization": "Bearer gt"}
    anon = gh_auth.TokenProvider(env={})
    assert anon.mode == "anonymous" and anon.auth_header() == {} and anon.invalidate() is False


# ---------------------------------------------------------------- gh_http rate limits


def test_403_with_reset_sleeps_until_reset_then_retries_same_request(monkeypatch, sleeps):
    now = time.time()
    net = FakeNet([
        (403, {"message": "API rate limit exceeded"}, {"X-RateLimit-Remaining": "0",
                                                        "X-RateLimit-Reset": str(int(now) + 100)}),
        (200, {"ok": True}, {"X-RateLimit-Remaining": "4999", "X-RateLimit-Limit": "5000"}),
    ])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    status, _h, body = gh_http.request("https://api.github.com/repos/a/b")
    assert status == 200 and json.loads(body) == {"ok": True}
    assert len(net.requests) == 2 and net.requests[0].full_url == net.requests[1].full_url
    assert len(sleeps) == 1 and 100 <= sleeps[0] <= 106          # until reset + 5 s
    assert gh_http.STATS["remaining"] == 4999


def test_retry_after_is_honoured_and_waits_do_not_consume_tries(monkeypatch, sleeps):
    net = FakeNet([(429, b"", {"Retry-After": "7"}), (429, b"", {"Retry-After": "3"}), (200, [], {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    kind, body = okf._fetch("https://api.github.com/repos/a/b", {}, tries=1)
    assert (kind, body) == ("ok", [])
    assert sleeps == [7.0, 3.0]


def test_third_hit_or_overlong_wait_returns_ratelimit(monkeypatch, sleeps):
    limited = (403, {"message": "You have exceeded a secondary rate limit"}, {})
    monkeypatch.setattr(urllib.request, "urlopen", FakeNet([limited, limited, limited]))
    assert okf._get_json_keyed("https://api.github.com/repos/a/b/stats/commit_activity") == "RATELIMIT"
    assert sleeps == [60.0, 120.0]                            # two waits, the third hit gives up

    sleeps.clear()
    far = str(int(time.time()) + 70 * 60)
    monkeypatch.setattr(urllib.request, "urlopen",
                        FakeNet([(403, b"", {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": far})]))
    with pytest.raises(gh_http.RateLimited):
        gh_http.request("https://api.github.com/repos/a/b")
    assert sleeps == []                                       # never sleeps past 65 minutes


def test_plain_403_is_a_per_repo_fact_not_a_rate_limit(monkeypatch, sleeps):
    monkeypatch.setattr(urllib.request, "urlopen",
                        FakeNet([(403, {"message": "Repository access blocked"}, {"X-RateLimit-Remaining": "4000"})]))
    assert okf._get_json_keyed("https://api.github.com/repos/a/b/stats/commit_activity") is None
    assert sleeps == []


def test_401_refreshes_app_token_once_and_retries(monkeypatch):
    clock = {"t": time.time()}
    gh_auth.reset(_app_provider(clock))
    net = FakeNet([(401, {"message": "Bad credentials"}, {}), (200, {"id": 1}, {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    status, _h, _b = gh_http.request("https://api.github.com/repos/a/b",
                                     headers={"Authorization": "Bearer stale-GITHUB_TOKEN"})
    assert status == 200
    auths = [r.get_header("Authorization") for r in net.requests]
    assert auths == ["Bearer ghs_tok1", "Bearer ghs_tok2"]   # App token overrides; refreshed after 401
    assert gh_http.STATS["auth_refreshes"] == 1


# ---------------------------------------------------------------- GraphQL


def _gql_node(full, i, owner="Organization"):
    return {"nameWithOwner": full, "databaseId": 1000 + i, "stargazerCount": i,
            "createdAt": "2024-01-02T03:04:05Z", "owner": {"__typename": owner}}


def test_graphql_batches_100_per_query_and_caches_nulls(monkeypatch, tmp_path):
    repos = [f"org{i}/repo{i}" for i in range(250)]
    queries = []

    def fake_post(query):
        queries.append(query)
        n = query.count("repository(")
        data = {"rateLimit": {"cost": 1, "remaining": 4000, "resetAt": "2026-09-26T20:00:00Z"}}
        for j in range(n):
            full = query.split("repository(")[j + 1].split('"')[1] + "/" + query.split("repository(")[j + 1].split('"')[3]
            idx = int(full.split("/")[0][3:])
            data[f"r{j}"] = None if idx == 5 else _gql_node(full, idx)
        return data, ([{"type": "NOT_FOUND"}] if any(v is None for v in data.values()) else [])

    monkeypatch.setattr(gh_graphql, "post_query", fake_post)
    cache = gh_graphql.prefetch(repos)
    assert [q.count("repository(") for q in queries] == [100, 100, 50]
    assert all("rateLimit { cost remaining resetAt }" in q for q in queries)
    assert 'r0: repository(owner: "org0", name: "repo0")' in queries[0]
    assert "nameWithOwner databaseId stargazerCount createdAt owner { __typename }" in queries[0]
    assert cache["org5/repo5"] is None and cache["org6/repo6"]["databaseId"] == 1006
    # resumable: a second prefetch sends nothing
    queries.clear()
    gh_graphql.prefetch(repos)
    assert queries == []
    assert (Path(os.environ["EVX_GH_CACHE_DIR"]) / "repo_meta.json").exists()


def test_graphql_failed_batch_is_halved(monkeypatch):
    calls = []

    def flaky(query):
        n = query.count("repository(")
        calls.append(n)
        if n > 2:
            raise gh_graphql.GraphQLError("GraphQL HTTP 502")
        return {f"r{j}": _gql_node(f"o/r{j}", j) for j in range(n)}, []

    monkeypatch.setattr(gh_graphql, "post_query", flaky)
    out = gh_graphql.fetch_batch([f"o/x{i}" for i in range(5)])
    assert calls == [5, 2, 3, 1, 2]                            # 5 -> 2+3 -> 3 -> 1+2
    assert sorted(out) == [f"o/x{i}" for i in range(5)] and all(out.values())


def test_graphql_low_budget_waits_for_reset(monkeypatch, sleeps):
    reset = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 300))
    monkeypatch.setattr(gh_graphql, "post_query", lambda q: (
        {"rateLimit": {"cost": 1, "remaining": 3, "resetAt": reset}, "r0": _gql_node("a/b", 1)}, []))
    gh_graphql.fetch_batch(["a/b"])
    assert len(sleeps) == 1 and 290 <= sleeps[0] <= 306


def test_graphql_rate_limited_error_waits_then_retries(monkeypatch, sleeps):
    reset = str(int(time.time()) + 60)
    net = FakeNet([
        (200, {"data": None, "errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}]},
         {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": reset}),
        (200, {"data": {"rateLimit": {"remaining": 4999, "resetAt": "2026-09-26T20:00:00Z"},
                        "r0": _gql_node("a/b", 1)}}, {}),
    ])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    out = gh_graphql.fetch_batch(["a/b"])
    assert out["a/b"]["databaseId"] == 1001
    assert len(sleeps) == 1 and 55 <= sleeps[0] <= 66
    assert gh_http.STATS["graphql"] == 2 and net.requests[0].get_method() == "POST"


def test_meta_served_from_graphql_cache_and_null_falls_back_to_rest(monkeypatch):
    gh_graphql.save_cache({"a/b": {"nameWithOwner": "A/b", "databaseId": 9, "stargazerCount": 77,
                                   "createdAt": "2023-05-06T00:00:00Z", "owner_type": "User"},
                           "gone/x": None})
    net = FakeNet([(200, {"stargazers_count": 5, "created_at": "2020-01-01T00:00:00Z"}, {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    meta = okf._get_json_keyed("https://api.github.com/repos/a/b", {"User-Agent": "t"})
    assert meta["stargazers_count"] == 77 and meta["created_at"][:10] == "2023-05-06"
    assert net.requests == []                                  # served without a request
    fallback = okf._get_json_keyed("https://api.github.com/repos/gone/x", {"User-Agent": "t"})
    assert fallback == {"stargazers_count": 5, "created_at": "2020-01-01T00:00:00Z"}
    assert [r.full_url for r in net.requests] == ["https://api.github.com/repos/gone/x"]


def test_cache_dir_must_be_outside_the_repo(monkeypatch):
    monkeypatch.setenv("EVX_GH_CACHE_DIR", str(REPO / "data" / "evx-gh"))
    with pytest.raises(ValueError, match="outside"):
        gh_graphql.cache_dir()


# ---------------------------------------------------------------- warm / capture

ACT = "https://api.github.com/repos/o/r/stats/commit_activity"
WEEKS = [{"total": 3, "week": 1}]


def test_warm_pass_one_request_202_recorded_not_retried(monkeypatch, sleeps):
    monkeypatch.setenv("EVX_PASS", "warm")
    okf._reset_run()
    net = FakeNet([(202, b"", {}), (200, WEEKS, {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    assert okf._get_json_keyed(ACT) is None
    assert len(net.requests) == 1 and sleeps == []
    assert okf.RUN["warm_202"] == ["o/r"]
    assert okf._get_json_keyed(ACT.replace("o/r", "o/s")) == WEEKS    # a 200 is cached
    assert okf._act_cache_get("o/s") == WEEKS and okf._act_cache_get("o/r") is None


def test_capture_serves_cache_and_retries_202_with_backoff(monkeypatch, sleeps):
    monkeypatch.setenv("EVX_PASS", "capture")
    okf._reset_run()
    okf._act_cache_put("o/cached", WEEKS)
    net = FakeNet([(202, b"", {}), (202, b"", {}), (202, b"", {}), (200, WEEKS, {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    assert okf._get_json_keyed(ACT.replace("o/r", "o/cached")) == WEEKS
    assert net.requests == []                                  # cached 200 served
    assert okf._get_json_keyed(ACT) == WEEKS
    assert sleeps == [2, 4, 8] and len(net.requests) == 4
    assert okf._act_cache_get("o/r") == WEEKS


def test_capture_gives_up_after_full_backoff_and_respects_budget(monkeypatch, sleeps):
    monkeypatch.setenv("EVX_PASS", "capture")
    okf._reset_run()
    monkeypatch.setattr(urllib.request, "urlopen", FakeNet([(202, b"", {})] * 6))
    assert okf._get_json_keyed(ACT) is None
    assert sleeps == [2, 4, 8, 16, 30]
    sleeps.clear()
    monkeypatch.setenv("EVX_202_WAIT_BUDGET_S", "0")           # budget spent: single attempt only
    monkeypatch.setattr(urllib.request, "urlopen", FakeNet([(202, b"", {})]))
    assert okf._get_json_keyed(ACT.replace("o/r", "o/t")) is None
    assert sleeps == []


def test_stale_cache_entries_are_ignored(monkeypatch):
    okf._act_cache_put("o/r", WEEKS)
    path = okf._act_path("o/r")
    payload = json.loads(path.read_text())
    payload["fetched_at"] -= 21 * 3600
    path.write_text(json.dumps(payload))
    assert okf._act_cache_get("o/r") is None


def test_warm_pass_runs_no_collector_and_writes_summary(monkeypatch, tmp_path, isolated_repo):
    import collect

    (isolated_repo / "etl" / "seeds.json").write_text(json.dumps(
        {"verticals": {"v": {"entities": [{"github_repo": "a/one"}, {"github_repo": "b/two"}]}}}))
    monkeypatch.setenv("EVX_PASS", "warm")
    monkeypatch.setattr(collect, "_get_json", collect._get_json)   # okf.main() rebinds it; restore after
    monkeypatch.setattr(collect, "main", lambda: pytest.fail("warm pass must not run the collector"))
    net = FakeNet([(202, b"", {}), (200, WEEKS, {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    assert okf.main() == 0
    cache = Path(os.environ["EVX_GH_CACHE_DIR"])
    assert json.loads((cache / "warm-202.json").read_text()) == ["a/one"]
    summary = json.loads((cache / "summary-warm.json").read_text())
    assert summary["repos"] == 2 and summary["rest_requests"] == 2
    assert not (isolated_repo / "data").exists()


# ---------------------------------------------------------------- date pin


def test_date_pin_moves_snapshot_date_but_not_captured_at(monkeypatch, isolated_repo):
    import collect

    (isolated_repo / "etl" / "seeds.json").write_text(json.dumps({
        "domain": {"slug": "ai", "label": "AI"},
        "verticals": {"v": {"label": "V — v", "industry_slug": "ind", "subniche_slug": "sub",
                            "entities": [{"github_repo": f"o/r{i}", "name": f"R{i}"} for i in range(3)]}}}))
    monkeypatch.setattr(collect, "date", collect.date)              # restored after the test
    pinned = okf.install_date_pin("2026-09-26")
    assert pinned == date(2026, 9, 26) and collect.date.today() == date(2026, 9, 26)

    def fake_get(url, headers=None, tries=5):
        if url.endswith("/commit_activity"):
            return [{"total": w % 5} for w in range(52)]
        return {"stargazers_count": 1, "created_at": "2024-01-01T00:00:00Z"}

    monkeypatch.setattr(collect, "_get_json", fake_get)
    monkeypatch.setattr(collect.time, "sleep", lambda s: None)
    collect.main()
    snap = json.loads((isolated_repo / "data" / "snapshots" / "2026-09-26" / "snapshot.json").read_text())
    assert snap["snapshot_date"] == "2026-09-26" and snap["period"] == "2026-w39"
    captured = snap["captured_at"]
    assert captured[:10] == time.strftime("%Y-%m-%d", time.gmtime())  # real UTC time, not the pin


def test_date_pin_rejects_malformed_values():
    with pytest.raises(SystemExit):
        okf.install_date_pin("26/09/2026")
    assert okf.install_date_pin("") is None


# ---------------------------------------------------------------- owner_classify


def test_owner_classify_from_graphql_payload_is_schema_compatible(tmp_path, monkeypatch):
    gh_graphql.save_cache({
        "org/tool": {"nameWithOwner": "Org/tool", "databaseId": 11, "stargazerCount": 1,
                     "createdAt": "2024-01-01T00:00:00Z", "owner_type": "Organization"},
        "person/lib": {"nameWithOwner": "person/lib", "databaseId": 12, "stargazerCount": 1,
                       "createdAt": "2024-01-01T00:00:00Z", "owner_type": "User"},
        "moved/old": None,
    })
    rest_calls = []

    def rest(repo):
        rest_calls.append(repo)
        return {"owner_type": "Organization", "repo_id": 13, "full_name": "moved/new"}

    monkeypatch.setattr(owner_classify, "_rest_classification", rest)
    id_map = tmp_path / "id_map.json"
    cache = tmp_path / "owner_types.json"
    id_map.write_text(json.dumps({"org/tool": "e_1", "person/lib": "e_2", "moved/old": "e_3"}))
    fetcher = owner_classify.graphql_fetcher(["org/tool", "person/lib", "moved/old"])
    assert owner_classify.refresh(id_map, cache, token="t", fetcher=fetcher) is True
    assert rest_calls == ["moved/old"]
    written = cache.read_text()
    expected = {"schema_version": "owner_types_1", "repos": {
        "moved/old": {"full_name": "moved/new", "owner_type": "Organization", "repo_id": 13},
        "org/tool": {"full_name": "Org/tool", "owner_type": "Organization", "repo_id": 11},
        "person/lib": {"full_name": "person/lib", "owner_type": "User", "repo_id": 12}}}
    assert written == json.dumps(expected, indent=2, sort_keys=True) + "\n"
    assert owner_classify.verify_cache(json.loads(id_map.read_text()), json.loads(written)) == []


def test_owner_classify_graphql_node_validation():
    with pytest.raises(ValueError, match=r"owner\.type"):
        owner_classify.classification_from_graphql("a/b", {"nameWithOwner": "a/b", "databaseId": 1,
                                                           "owner_type": "Enterprise"})


# ---------------------------------------------------------------- t2_collect


def test_t2_fetch_waits_out_rate_limit_and_uses_app_token(monkeypatch, sleeps):
    clock = {"t": time.time()}
    gh_auth.reset(_app_provider(clock))
    reset = str(int(time.time()) + 30)
    net = FakeNet([(403, {"message": "API rate limit exceeded"}, {"X-RateLimit-Remaining": "0",
                                                                   "X-RateLimit-Reset": reset}),
                   (200, b'{"subscribers_count": 1}', {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    status, body = t2_collect._fetch("https://api.github.com/repos/a/b", "fallback-token")
    assert (status, body) == (200, b'{"subscribers_count": 1}')        # raw bytes kept for sha256
    assert len(sleeps) == 1 and 30 <= sleeps[0] <= 36
    assert {r.get_header("Authorization") for r in net.requests} == {"Bearer ghs_tok1"}


def test_t2_fetch_keeps_explicit_token_without_app(monkeypatch):
    net = FakeNet([(200, b"{}", {})])
    monkeypatch.setattr(urllib.request, "urlopen", net)
    assert t2_collect._fetch("https://api.github.com/repos/a/b", "tok") == (200, b"{}")
    assert net.requests[0].get_header("Authorization") == "Bearer tok"


def test_dead_seeds_fail_fast_unless_allowed(monkeypatch, tmp_path):
    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps({"verticals": {"v": {"entities": [
        {"github_repo": "live/one"}, {"github_repo": "renamed/two"}, {"github_repo": "gone/three"}]}}}))
    monkeypatch.setattr(gh_graphql, "SEEDS_PATH", seeds)
    monkeypatch.setattr(gh_graphql, "report_budget", lambda: {"auth_mode": "token"})
    monkeypatch.setattr(gh_graphql, "post_query", lambda q: (
        {"r0": _gql_node("live/one", 1), "r1": None, "r2": None}, [{"type": "NOT_FOUND"}]))
    monkeypatch.setattr(gh_graphql.seed_repos, "__defaults__", (seeds,))
    net = FakeNet([(200, {"id": 2}, {}), (404, {"message": "Not Found"}, {})] * 2)
    monkeypatch.setattr(urllib.request, "urlopen", net)
    assert gh_graphql.main() == 1
    cache = Path(os.environ["EVX_GH_CACHE_DIR"])
    assert json.loads((cache / "dead-seeds.json").read_text()) == ["gone/three"]
    monkeypatch.setenv("EVX_ALLOW_DEAD_SEEDS", "1")
    assert gh_graphql.main() == 0
