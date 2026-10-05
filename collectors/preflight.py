#!/usr/bin/env python3
"""Check all seeds before collection; report every departure and ownership move."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gh_auth
import gh_graphql
import owner_classify


def inspect(repos: list[str], registry: dict, token: str, fetcher: Callable,
            day: str) -> dict:
    report = {"date": day, "checked": 0, "departed": [], "moves": [], "errors": []}
    for repo in repos:
        report["checked"] += 1
        try:
            entry = fetcher(repo, token)
        except owner_classify.RepositoryHTTPError as exc:
            if exc.status in gh_graphql.GONE_STATUSES:
                report["departed"].append({"date": day, "github_repo": repo, "github_status": exc.status})
            else:
                report["errors"].append({"github_repo": repo, "error": str(exc)})
            continue
        except Exception as exc:
            # One failure must not hide the rest of the remediation list.
            report["errors"].append({"github_repo": repo, "error": str(exc)})
            continue
        old = registry.get(repo, {})
        reasons = []
        if entry["full_name"].lower() != old.get("full_name", repo).lower():
            reasons.append("repository moved")
        if old.get("owner_type") and old["owner_type"] != entry["owner_type"]:
            reasons.append("owner type changed; confirmation required")
        if old.get("repo_id") and old["repo_id"] != entry["repo_id"]:
            reasons.append("repository identity changed")
        if reasons:
            report["moves"].append({"github_repo": repo, **entry, "reasons": reasons})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=Path, default=gh_graphql.SEEDS_PATH)
    parser.add_argument("--owners", type=Path, default=owner_classify.CACHE_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    token = gh_auth.token()
    if not token:
        print("preflight requires GitHub credentials", file=sys.stderr)
        return 1
    repos = gh_graphql.seed_repos(args.seeds)
    registry = json.loads(args.owners.read_text())["repos"]
    # Refresh once, then share the cache with the expensive weekly collection.
    # GraphQL null is not proof of 404: the shared fetcher confirms misses via REST.
    fetcher = owner_classify.graphql_fetcher(repos, fresh=True)
    day = datetime.now(timezone.utc).date().isoformat()
    report = inspect(repos, registry, token, fetcher, day)
    output = args.output or gh_graphql.cache_dir() / "preflight.json"
    gh_graphql.atomic_write_json(output, report)
    print(json.dumps(report, indent=2))
    print(f"preflight report: {output}")
    return int(any(report[key] for key in ("departed", "moves", "errors")))


if __name__ == "__main__":
    raise SystemExit(main())
