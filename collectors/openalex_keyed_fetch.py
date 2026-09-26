"""openalex_keyed_fetch - STAGED forward fetch-layer hardening for axis-2.

Why: OpenAlex retired the polite pool / mailto parameter on 2026-02-13 and now
requires an API key (free tier: 100,000 credits/day; keyless: ~100 credits,
then HTTP 409). The frozen collector (etl/collect.py) still appends the dead
mailto param and, on failure, silently degrades axis-2 to 'absent' - a
silent-series-rot class defect: today's 14 calls/run squeeze under the demo
allowance, but any coverage expansion crosses the cliff without an alarm.

What this wrapper does (fetch layer ONLY; scoring semantics untouched):
  * rewrites api.openalex.org URLs: strips the dead `mailto=` param, appends
    `api_key=` from env OPENALEX_API_KEY (or a gitignored etl/.env);
  * HARD-FAILS (exit 3) on HTTP 409 credit exhaustion for OpenAlex calls -
    a loud [THREAT] instead of a silent axis-2 'absent';
  * without a key, request URLs stay byte-identical (keyless demo allowance)
    plus a loud warning; the 409 hard-fail above still applies keyless too;
  * delegates every non-OpenAlex URL to the frozen collector's own fetcher.

STATUS: WIRED (2026-07-02). The weekly workflow's collect step runs this
wrapper; OPENALEX_API_KEY lives in repo secrets and the keeper's gitignored
etl/.env. The m-version is NOT bumped: transport is not methodology - the
frozen collector, the formula fingerprint, and every published number are
untouched (recorded in METHODOLOGY-VERSIONING.md operational notes).

GitHub fetch layer (2026-09-26, 5,939 seeded systems; the built-in token died on
the first 403 and the old path returned "RATELIMIT" on it, aborting the run):
  * every api.github.com request goes through collectors/gh_http.py: App
    installation token (collectors/gh_auth.py) or GITHUB_TOKEN, rate limits
    waited out (sleep until reset + 5 s, same request retried), 401 -> one
    token refresh. "RATELIMIT" is returned only when a single wait would exceed
    65 minutes or the same request hit the limit 3 times;
  * `repos/{repo}` is answered from the GraphQL metadata cache
    (collectors/gh_graphql.py) with the REST field names the collector reads,
    REST on a miss;
  * `stats/commit_activity` 200 bodies are cached outside the repo tree.
    EVX_PASS=warm: one request per repository (a 202 is recorded, not retried),
    no collector run, nothing written to the repo. EVX_PASS=capture (default):
    cached 200s served, the rest requested with 202 retries after 2/4/8/16/30 s
    (bounded overall by EVX_202_WAIT_BUDGET_S);
  * SNAPSHOT_DATE=YYYY-MM-DD pins the collector's snapshot date (its date.today)
    while captured_at stays the real UTC time;
  * a progress line every 250 repositories (rate budget, elapsed; no secrets).

Pure standard library. etl/collect.py is never edited (byte-frozen).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "etl"))
sys.path.insert(0, str(REPO / "collectors"))

import collect  # the frozen collector, imported, never edited
import gh_graphql
import gh_http

_ORIG_GET_JSON = collect._get_json
_WARNED = False


def _mask(url: str) -> str:
    """Never let the api_key reach logs."""
    return re.sub(r"api_key=[^&]+", "api_key=***", url)


def _load_key() -> str:
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if key:
        return key
    env = REPO / "etl" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            m = re.match(r"\s*OPENALEX_API_KEY\s*=\s*(\S+)", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return ""


def _rewrite(url: str, key: str) -> str:
    base, _, query = url.partition("?")
    params = [p for p in query.split("&") if p and not p.startswith("mailto=")]
    params.append(f"api_key={key}")
    return base + "?" + "&".join(params)


def _get_json_keyed(url, headers=None, tries=5):
    global _WARNED
    if url.startswith(GITHUB_API):
        return _github_get(url, headers, tries)
    if "api.openalex.org" not in url:
        return _ORIG_GET_JSON(url, headers=headers, tries=tries)

    key = _load_key()
    if key:
        url = _rewrite(url, key)
    elif not _WARNED:
        _WARNED = True
        print("WARNING: OPENALEX_API_KEY not set - running on the keyless demo "
              "allowance (~100 credits, then HTTP 409). Get a free key at "
              "https://openalex.org/settings/api-key and put it in etl/.env")

    # Own request path for OpenAlex so a 409 can NEVER be swallowed into a
    # silent axis-2 'absent' (the frozen fetcher's generic retry would).
    import json as _json
    import time as _time
    import urllib.request as _rq
    for _ in range(tries):
        try:
            req = _rq.Request(url, headers=headers or {"User-Agent": "evidaxis-collect/2.0"})
            with _rq.urlopen(req, timeout=40) as r:
                return _json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 409:
                print("[THREAT] OpenAlex HTTP 409: API credits exhausted. "
                      "Axis-2 input is UNAVAILABLE - refusing to publish a "
                      "silently degraded snapshot. Provide/upgrade "
                      "OPENALEX_API_KEY and re-run.")
                raise SystemExit(3) from None
            if e.code in (403, 429):
                print(f"  rate-limit {e.code} on {_mask(url)[:70]}")
                return "RATELIMIT"
            if e.code == 404:
                return None
            _time.sleep(1.0)
        except Exception as ex:  # mirror the frozen fetcher's resilience
            print(f"  err {type(ex).__name__} {_mask(url)[:70]}")
            _time.sleep(1.0)
    return None


# ---------------------------------------------------------------- GitHub

GITHUB_API = "https://api.github.com/"
_META_RE = re.compile(r"^https://api\.github\.com/repos/([^/?#]+/[^/?#]+)$")
_ACT_RE = re.compile(r"^https://api\.github\.com/repos/([^/?#]+/[^/?#]+)/stats/commit_activity$")
BACKOFF_202 = (2, 4, 8, 16, 30)
PROGRESS_EVERY = 250
MAX_CONSECUTIVE_401 = 20

RUN: dict = {}


def _reset_run() -> None:
    RUN.clear()
    RUN.update({"pass": _pass(), "repos": 0, "meta_cache_hits": 0, "meta_rest": 0,
                "act_cache_hits": 0, "act_200": 0, "act_202_final": 0, "act_202_retries": 0,
                "act_none": 0, "wait_202_s": 0.0, "ratelimit_returned": 0, "warm_202": [],
                "started": time.time()})
    _META.clear()


_META: dict = {}


def _pass() -> str:
    return (os.environ.get("EVX_PASS") or "capture").strip().lower()


def _budget_202() -> float:
    try:
        return float(os.environ.get("EVX_202_WAIT_BUDGET_S", "2700"))
    except ValueError:
        return 2700.0


def _meta_cache() -> dict:
    if "repos" not in _META:
        try:
            _META["repos"] = gh_graphql.load_cache()
        except Exception as exc:  # an unusable cache only costs REST calls
            print(f"  graphql cache unavailable ({type(exc).__name__}); REST for repository metadata")
            _META["repos"] = {}
    return _META["repos"]


def _act_path(repo: str) -> Path:
    return gh_graphql.cache_dir() / "commit_activity" / (urllib.parse.quote(repo.lower(), safe="") + ".json")


def _act_cache_get(repo: str):
    try:
        payload = json.loads(_act_path(repo).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or time.time() - float(payload.get("fetched_at", 0)) > gh_graphql.max_age_s():
        return None
    return payload.get("body")


def _act_cache_put(repo: str, body) -> None:
    try:
        gh_graphql.atomic_write_json(_act_path(repo), {"fetched_at": time.time(), "body": body})
    except OSError as exc:
        print(f"  cache write failed for {repo}: {type(exc).__name__}")


def _progress_tick() -> None:
    RUN["repos"] += 1
    if RUN["repos"] % PROGRESS_EVERY == 0:
        print(f"[progress] pass={RUN['pass']} repos={RUN['repos']} | {gh_http.budget_line()} | "
              f"cache_hits={RUN['act_cache_hits']} 202={RUN['act_202_final']} | "
              f"elapsed={int(time.time() - RUN['started'])}s", flush=True)


def _fetch(url, headers, tries, backoff_202=()):
    """-> ("ok", json) | ("202", None) | ("none", None) | ("ratelimit", None)."""
    delays = list(backoff_202)
    attempt = 0
    while attempt < tries:
        try:
            status, _hdrs, body = gh_http.request(url, headers=dict(headers or {}))
        except gh_http.RateLimited as exc:
            print(f"  rate-limit on {url[:70]}: {exc}")
            RUN["ratelimit_returned"] = RUN.get("ratelimit_returned", 0) + 1
            return "ratelimit", None
        except Exception as ex:  # mirror the frozen fetcher's resilience
            print(f"  err {type(ex).__name__} {url[:70]}")
            attempt += 1
            time.sleep(1.0)
            continue
        if status == 200:
            try:
                return "ok", json.loads(body.decode())
            except ValueError:
                attempt += 1
                time.sleep(1.0)
                continue
        if status == 202:
            if delays and RUN.get("wait_202_s", 0.0) < _budget_202():
                delay = delays.pop(0)
                RUN["act_202_retries"] = RUN.get("act_202_retries", 0) + 1
                RUN["wait_202_s"] = RUN.get("wait_202_s", 0.0) + delay
                time.sleep(delay)
                continue
            return "202", None
        if status == 401:
            RUN["consecutive_401"] = RUN.get("consecutive_401", 0) + 1
            if RUN["consecutive_401"] >= MAX_CONSECUTIVE_401:
                print(f"[THREAT] GitHub rejected the credentials {RUN['consecutive_401']} times in a row (401) - "
                      "refusing to spend the run on a dead token.")
                raise SystemExit(4)
            return "none", None
        RUN["consecutive_401"] = 0
        if status in (204, 403, 404, 409, 410, 422, 451):
            return "none", None       # empty, blocked, gone: a per-repository fact (recorded by the gate)
        attempt += 1
        time.sleep(1.0)
    return "none", None


def _commit_activity(repo, url, headers, tries):
    mode = _pass()
    cached = _act_cache_get(repo)
    if cached is not None:
        RUN["act_cache_hits"] += 1
        _progress_tick()
        return cached
    backoff = () if mode == "warm" else BACKOFF_202
    kind, body = _fetch(url, headers, tries, backoff)
    _progress_tick()
    if kind == "ok":
        RUN["act_200"] += 1
        _act_cache_put(repo, body)
        return body
    if kind == "202":
        RUN["act_202_final"] += 1
        if mode == "warm":
            RUN["warm_202"].append(repo)
        return None
    if kind == "ratelimit":
        return "RATELIMIT"
    RUN["act_none"] += 1
    return None


def _github_get(url, headers, tries):
    m = _META_RE.match(url)
    if m:
        node = _meta_cache().get(m.group(1).lower())
        if node:
            RUN["meta_cache_hits"] += 1
            return gh_graphql.as_rest_meta(node)
        RUN["meta_rest"] += 1
        kind, body = _fetch(url, headers, tries)
        return body if kind == "ok" else ("RATELIMIT" if kind == "ratelimit" else None)
    m = _ACT_RE.match(url)
    if m:
        return _commit_activity(m.group(1), url, headers, tries)
    kind, body = _fetch(url, headers, tries)
    return body if kind == "ok" else ("RATELIMIT" if kind == "ratelimit" else None)


# ---------------------------------------------------------------- date pin


def install_date_pin(value=None):
    """SNAPSHOT_DATE=YYYY-MM-DD -> the frozen collector's date.today() returns that date.

    Only `collect.date` is replaced; `collect.datetime` (captured_at) stays real UTC.
    """
    value = (value if value is not None else os.environ.get("SNAPSHOT_DATE", "")).strip()
    if not value:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise SystemExit(f"SNAPSHOT_DATE must be YYYY-MM-DD, got {value!r}")
    pinned = date.fromisoformat(value)

    class _PinnedDate(date):
        @classmethod
        def today(cls):
            return pinned

    collect.date = _PinnedDate
    print(f"date pin: snapshot_date={pinned.isoformat()} (captured_at stays real UTC time)")
    return pinned


# ---------------------------------------------------------------- passes


def _write_summary() -> None:
    try:
        summary = {k: v for k, v in RUN.items() if k != "warm_202"}
        summary.update({"warm_202_count": len(RUN.get("warm_202", [])),
                        "rest_requests": gh_http.STATS["rest"], "graphql_requests": gh_http.STATS["graphql"],
                        "rate_waits": gh_http.STATS["rate_waits"], "rate_wait_s": int(gh_http.STATS["rate_wait_s"]),
                        "auth_refreshes": gh_http.STATS["auth_refreshes"],
                        "rate_remaining_end": gh_http.STATS.get("remaining"),
                        "elapsed_s": int(time.time() - RUN["started"])})
        out = gh_graphql.cache_dir()
        gh_graphql.atomic_write_json(out / f"summary-{RUN['pass']}.json", summary)
        if RUN["pass"] == "warm":
            gh_graphql.atomic_write_json(out / "warm-202.json", sorted(RUN.get("warm_202", [])))
        print(f"[summary] pass={RUN['pass']} repos={RUN['repos']} 200={RUN['act_200']} "
              f"cache_hits={RUN['act_cache_hits']} 202={RUN['act_202_final']} none={RUN['act_none']} "
              f"meta_cache_hits={RUN['meta_cache_hits']} meta_rest={RUN['meta_rest']} | {gh_http.budget_line()} | "
              f"elapsed={summary['elapsed_s']}s", flush=True)
    except Exception as exc:  # a summary must never fail the collection
        print(f"  summary not written: {type(exc).__name__}")


def warm_pass() -> int:
    """One /stats/commit_activity request per seeded repository; the collector does not run."""
    repos = gh_graphql.seed_repos(collect.ROOT / "seeds.json")
    print(f"warm pass: {len(repos)} repositories (one request each; 202s recorded, not retried)")
    for repo in repos:
        out = _get_json_keyed(f"https://api.github.com/repos/{repo}/stats/commit_activity", collect.GH_HDR)
        if out == "RATELIMIT":
            print("::warning::warm pass stopped on a rate limit that could not be waited out; "
                  "the capture pass requests the rest")
            break
    _write_summary()
    return 0


def capture_pass() -> int:
    install_date_pin()
    collect.main()
    _write_summary()
    if RUN.get("ratelimit_returned"):
        print("[THREAT] the collector aborted on a GitHub rate limit that could not be waited out "
              "(single wait > 65 min, or 3 hits on one request) - no complete snapshot this run.")
        return 2
    return 0


_reset_run()


def main() -> int:
    collect._get_json = _get_json_keyed
    _reset_run()
    if RUN["pass"] == "warm":
        return warm_pass()
    return capture_pass()


if __name__ == "__main__":
    sys.exit(main())
