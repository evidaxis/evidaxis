#!/usr/bin/env python3
"""gh_graphql - repository metadata for every seeded system, 100 per GraphQL query.

Why: the frozen collector and owner_classify each spent one REST call per repository
on `repos/{repo}` (~12,000 calls at 5,939 systems). One aliased GraphQL query answers
100 repositories for ~1 point of the separate GraphQL budget.

Fetched per repository: nameWithOwner databaseId stargazerCount createdAt
owner{__typename}. Written to a cache file outside the repo tree
(env EVX_GH_CACHE_DIR, else $RUNNER_TEMP/evx-gh, else the system temp dir).
A repository GraphQL answers null for (renamed, deleted, blocked) is cached as null
and its consumers fall back to REST individually. The query carries
rateLimit{cost remaining resetAt}; the fetcher sleeps until resetAt when the budget
runs low. A batch that fails is halved (a heavy batch can overrun GitHub's
server-side time budget), down to single repositories.

Usage:
  python3 collectors/gh_graphql.py            # prefetch all repositories in etl/seeds.json
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gh_http

REPO = HERE.parent
SEEDS_PATH = REPO / "etl" / "seeds.json"
GRAPHQL_URL = "https://api.github.com/graphql"
BATCH_SIZE = 100
FIELDS = "nameWithOwner databaseId stargazerCount createdAt owner { __typename }"
META_FILE = "repo_meta.json"
META_SCHEMA = "gh_meta_1"
LOW_BUDGET = 50                 # below this many GraphQL points left, wait for resetAt
ATTEMPTS = 3


class GraphQLError(RuntimeError):
    pass


def cache_dir() -> Path:
    raw = os.environ.get("EVX_GH_CACHE_DIR", "").strip()
    if not raw:
        base = os.environ.get("RUNNER_TEMP", "").strip() or tempfile.gettempdir()
        raw = os.path.join(base, "evx-gh")
    path = Path(raw).resolve()
    if path == REPO or REPO in path.parents:
        raise ValueError(f"EVX_GH_CACHE_DIR must be outside the repository tree: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def max_age_s() -> float:
    try:
        return float(os.environ.get("EVX_CACHE_MAX_AGE_H", "20")) * 3600
    except ValueError:
        return 20 * 3600.0


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=path.name + ".", delete=False) as tmp:
        json.dump(payload, tmp, separators=(",", ":"))
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def seed_repos(seeds_path: Path = SEEDS_PATH) -> list[str]:
    seeds = json.loads(seeds_path.read_text())
    seen: set[str] = set()
    out: list[str] = []
    for vertical in seeds["verticals"].values():
        for ent in vertical["entities"]:
            repo = ent["github_repo"]
            if repo.lower() not in seen:
                seen.add(repo.lower())
                out.append(repo)
    return out


# ---------------------------------------------------------------- cache


def load_cache(path: Path | None = None) -> dict[str, dict | None]:
    """{repo_lower: node-or-None}; a stale or unreadable file counts as empty."""
    path = path or cache_dir() / META_FILE
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict) or payload.get("v") != META_SCHEMA:
        return {}
    if time.time() - float(payload.get("created_at", 0)) > max_age_s():
        return {}
    repos = payload.get("repos")
    return repos if isinstance(repos, dict) else {}


def save_cache(repos: dict[str, dict | None], path: Path | None = None, created_at: float | None = None) -> None:
    path = path or cache_dir() / META_FILE
    atomic_write_json(path, {"v": META_SCHEMA, "created_at": created_at or time.time(), "repos": repos})


def as_rest_meta(node: dict) -> dict:
    """The REST `repos/{repo}` field names the frozen collector reads."""
    return {"id": node["databaseId"], "full_name": node["nameWithOwner"],
            "stargazers_count": node["stargazerCount"], "created_at": node["createdAt"]}


def _node(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict) or not raw.get("nameWithOwner") or raw.get("databaseId") is None:
        return None
    return {"nameWithOwner": raw["nameWithOwner"], "databaseId": raw["databaseId"],
            "stargazerCount": raw.get("stargazerCount") or 0, "createdAt": raw.get("createdAt"),
            "owner_type": (raw.get("owner") or {}).get("__typename")}


# ---------------------------------------------------------------- query


def build_query(repos: list[str]) -> str:
    parts = []
    for i, full in enumerate(repos):
        owner, _, name = full.partition("/")
        parts.append(f"r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {FIELDS} }}")
    return "query { rateLimit { cost remaining resetAt } " + " ".join(parts) + " }"


def _reset_epoch(reset_at: Any) -> float | None:
    try:
        return datetime.strptime(str(reset_at), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _wait_for_reset(reset_at: Any, why: str, epoch: float | None = None) -> None:
    epoch = epoch if epoch is not None else _reset_epoch(reset_at)
    wait = (max(0.0, epoch - time.time()) if epoch else gh_http.NO_HEADER_WAIT_S) + gh_http.RESET_PAD_S
    if wait > gh_http.MAX_SINGLE_WAIT_S:
        raise gh_http.RateLimited(f"GraphQL budget reset is {int(wait)}s away")
    print(f"  graphql {why}: sleeping {int(wait)}s until resetAt {reset_at}", flush=True)
    gh_http.STATS["rate_waits"] += 1
    gh_http.STATS["rate_wait_s"] += wait
    time.sleep(wait)


def post_query(query: str) -> tuple[dict, list]:
    """POST one query -> (data, errors). Raises GraphQLError when it cannot be answered."""
    body = json.dumps({"query": query}).encode()
    limited = 0
    attempt = 0
    while attempt < ATTEMPTS:
        try:
            status, _hdrs, raw = gh_http.request(GRAPHQL_URL, method="POST", data=body, timeout=60,
                                                 headers={"Content-Type": "application/json"}, kind="graphql")
        except gh_http.RateLimited:
            raise
        except Exception as exc:  # transport: retry, then let the caller halve the batch
            print(f"  graphql err {type(exc).__name__}", flush=True)
            attempt += 1
            time.sleep(2 ** attempt)
            continue
        if status == 200:
            try:
                payload = json.loads(raw.decode())
            except ValueError:
                attempt += 1
                continue
            errors = payload.get("errors") or []
            if any(isinstance(e, dict) and e.get("type") == "RATE_LIMITED" for e in errors):
                limited += 1
                if limited >= gh_http.MAX_LIMIT_HITS:
                    raise gh_http.RateLimited("GraphQL RATE_LIMITED 3 times on the same query")
                rate = ((payload.get("data") or {}).get("rateLimit") or {})
                hdr_reset = gh_http._header(_hdrs, "X-RateLimit-Reset")
                epoch = None
                if not rate.get("resetAt") and hdr_reset:
                    try:
                        epoch = float(hdr_reset)
                    except ValueError:
                        epoch = None
                _wait_for_reset(rate.get("resetAt"), "RATE_LIMITED", epoch)
                continue          # waiting does not consume an attempt
            data = payload.get("data")
            if not isinstance(data, dict):
                raise GraphQLError(f"GraphQL answered without data ({len(errors)} error(s))")
            return data, errors
        attempt += 1
        if status >= 500 and attempt < ATTEMPTS:
            time.sleep(2 ** attempt)
            continue
        raise GraphQLError(f"GraphQL HTTP {status}")
    raise GraphQLError("GraphQL failed after retries")


def fetch_batch(repos: list[str]) -> dict[str, dict | None]:
    """{repo_lower: node-or-None} for up to BATCH_SIZE repositories; halves on failure.

    A repository whose single-item query still fails is left OUT of the result
    (uncached), so its consumers go to REST for it.
    """
    try:
        data, _errors = post_query(build_query(repos))
    except GraphQLError as exc:
        if len(repos) == 1:
            print(f"  graphql gave up on {repos[0]}: {exc}; REST fallback", flush=True)
            return {}
        mid = len(repos) // 2
        print(f"  graphql batch of {len(repos)} failed ({exc}); halving", flush=True)
        out = fetch_batch(repos[:mid])
        out.update(fetch_batch(repos[mid:]))
        return out
    out: dict[str, dict | None] = {}
    for i, repo in enumerate(repos):
        out[repo.lower()] = _node(data.get(f"r{i}"))
    rate = data.get("rateLimit") or {}
    remaining = rate.get("remaining")
    if isinstance(remaining, int):
        gh_http.STATS["graphql_remaining"] = remaining
        if remaining < LOW_BUDGET:
            _wait_for_reset(rate.get("resetAt"), f"budget low ({remaining} points)")
    return out


def prefetch(repos: list[str], path: Path | None = None, batch_size: int = BATCH_SIZE) -> dict[str, dict | None]:
    """Fill the metadata cache for `repos` (resumable: fresh cached entries are kept)."""
    path = path or cache_dir() / META_FILE
    cache = load_cache(path)
    created_at = time.time()
    if cache:
        try:
            created_at = float(json.loads(path.read_text()).get("created_at"))
        except (OSError, ValueError, TypeError):
            created_at = time.time()
    todo = [r for r in repos if r.lower() not in cache]
    started = time.time()
    print(f"[gh_graphql] {len(repos)} repositories: {len(repos) - len(todo)} cached, "
          f"{len(todo)} to fetch in batches of {batch_size}", flush=True)
    for n, i in enumerate(range(0, len(todo), batch_size), start=1):
        cache.update(fetch_batch(todo[i:i + batch_size]))
        save_cache(cache, path, created_at)
        if n % 10 == 0:
            print(f"[gh_graphql] {min(i + batch_size, len(todo))}/{len(todo)} fetched | "
                  f"{gh_http.budget_line()} | elapsed {int(time.time() - started)}s", flush=True)
    nulls = sum(1 for r in repos if cache.get(r.lower()) is None)
    print(f"[gh_graphql] done: {len(repos) - nulls} resolved, {nulls} null/missing -> REST fallback | "
          f"{gh_http.budget_line()} | elapsed {int(time.time() - started)}s", flush=True)
    return cache


def report_budget() -> dict:
    """Print which credentials are in use and the REST/GraphQL budgets (GET /rate_limit is free)."""
    import gh_auth
    info: dict[str, Any] = {"auth_mode": gh_auth.mode()}
    try:
        status, _h, raw = gh_http.request("https://api.github.com/rate_limit", kind="meta")
        if status == 200:
            res = json.loads(raw.decode()).get("resources", {})
            for key in ("core", "graphql"):
                info[key] = {k: res.get(key, {}).get(k) for k in ("limit", "remaining", "reset")}
    except Exception as exc:
        info["error"] = type(exc).__name__
    print(f"[gh_graphql] auth={info['auth_mode']} core={info.get('core')} graphql={info.get('graphql')}", flush=True)
    if info["auth_mode"] != "app":
        print("::warning::GitHub App credentials (COLLECT_APP_ID/COLLECT_APP_KEY) are not set - running on "
              "GITHUB_TOKEN, whose budget cannot carry the full universe in one job", flush=True)
    return info


GONE_STATUSES = (404, 410, 451)


def dead_seeds(repos: list[str], cache: dict[str, dict | None]) -> list[str]:
    """Seeds GraphQL could not resolve AND REST confirms gone (404/410/451).

    The frozen collector puts every seed into etl/id_map.json, and owner_classify
    must classify every id_map entry, so a dead seed fails the run AFTER hours of
    collection. Found here it costs one REST call per GraphQL null.
    """
    dead = []
    for repo in repos:
        if cache.get(repo.lower()) is not None:
            continue
        try:
            status, _h, _b = gh_http.request(f"https://api.github.com/repos/{repo}")
        except gh_http.RateLimited:
            raise
        except Exception:
            continue
        if status in GONE_STATUSES:
            dead.append(repo)
    return dead


def main() -> int:
    repos = seed_repos()
    budget = report_budget()
    try:
        cache = prefetch(repos)
        dead = dead_seeds(repos, cache)
    except gh_http.RateLimited as exc:
        print(f"[gh_graphql] rate limit could not be waited out ({exc}); consumers fall back to REST")
        return 0
    if dead:
        atomic_write_json(cache_dir() / "dead-seeds.json", dead)
        msg = (f"{len(dead)} seeded repositories are gone on GitHub (REST 404/410/451): {', '.join(dead)}. "
               "The collector will drop them (declared gaps), but owner_classify cannot classify them and "
               "fails the run after collection. Remove them from etl/seeds.json before a real run.")
        if os.environ.get("EVX_ALLOW_DEAD_SEEDS", "").strip() == "1":
            print(f"::warning::{msg}", flush=True)
        else:
            print(f"::error::{msg}", flush=True)
            return 1
    summary = {"budget_at_start": budget, "dead_seeds": dead, "repos": len(repos), "resolved": sum(1 for r in repos if cache.get(r.lower())),
               "graphql_requests": gh_http.STATS["graphql"], "rest_requests": gh_http.STATS["rest"],
               "rate_waits": gh_http.STATS["rate_waits"], "elapsed_s": int(time.time() - gh_http.STATS["started"])}
    atomic_write_json(cache_dir() / "summary-graphql.json", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
