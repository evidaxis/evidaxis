#!/usr/bin/env python3
"""Classify canonical GitHub repository ownership for publication policy."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent
ID_MAP_PATH = REPO / "etl/id_map.json"
CACHE_PATH = REPO / "etl/owner_types.json"
SCHEMA_VERSION = "owner_types_1"
ALLOWED_FIELDS = {"owner_type", "repo_id", "full_name"}
ALLOWED_TYPES = {"Organization", "User"}
GITHUB_API = "https://api.github.com/repos/{repo}"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def verify_cache(id_map: dict[str, str], cache: Any) -> list[str]:
    errors: list[str] = []
    if (
        not isinstance(cache, dict)
        or set(cache) != {"schema_version", "repos"}
        or cache.get("schema_version") != SCHEMA_VERSION
    ):
        return [f"cache schema_version must be {SCHEMA_VERSION}"]
    repos = cache.get("repos")
    if not isinstance(repos, dict):
        return ["cache repos must be an object"]
    if set(repos) != set(id_map):
        missing = sorted(set(id_map) - set(repos))
        extra = sorted(set(repos) - set(id_map))
        errors.append(f"cache coverage mismatch; missing={missing}, extra={extra}")
    for repo, entry in repos.items():
        if not isinstance(entry, dict) or set(entry) != ALLOWED_FIELDS:
            errors.append(f"{repo}: fields must be {sorted(ALLOWED_FIELDS)}")
            continue
        if entry.get("owner_type") not in ALLOWED_TYPES:
            errors.append(f"{repo}: owner_type must be Organization or User")
        repo_id = entry.get("repo_id")
        if not isinstance(repo_id, int) or isinstance(repo_id, bool) or repo_id <= 0:
            errors.append(f"{repo}: repo_id must be a positive integer")
        full_name = entry.get("full_name")
        if not isinstance(full_name, str) or len(full_name.split("/")) != 2 or not all(full_name.split("/")):
            errors.append(f"{repo}: full_name must be owner/repository")
    return errors


def fetch_classification(
    repo: str,
    token: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    headers = {
        "User-Agent": "evidaxis-owner-classifier",
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    request = urllib.request.Request(GITHUB_API.format(repo=repo), headers=headers)
    with opener(request, timeout=40) as response:
        payload = json.loads(response.read())
    owner = payload.get("owner")
    owner_type = owner.get("type") if isinstance(owner, dict) else None
    repo_id = payload.get("id")
    full_name = payload.get("full_name")
    if owner_type not in ALLOWED_TYPES:
        raise ValueError(f"{repo}: GitHub owner.type is not supported: {owner_type!r}")
    if not isinstance(repo_id, int) or isinstance(repo_id, bool) or repo_id <= 0:
        raise ValueError(f"{repo}: GitHub repository id is unavailable")
    if not isinstance(full_name, str) or len(full_name.split("/")) != 2 or not all(full_name.split("/")):
        raise ValueError(f"{repo}: GitHub canonical full_name is malformed")
    return {"owner_type": owner_type, "repo_id": repo_id, "full_name": full_name}


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=path.name + ".", delete=False) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        temp_path = Path(tmp.name)
    os.replace(temp_path, path)


def refresh(
    id_map_path: Path = ID_MAP_PATH,
    cache_path: Path = CACHE_PATH,
    token: str | None = None,
    fetcher: Callable[[str, str], dict[str, Any]] = fetch_classification,
) -> bool:
    id_map = _read_json(id_map_path)
    old_cache = _read_json(cache_path) if cache_path.exists() else {"schema_version": SCHEMA_VERSION, "repos": {}}
    if not token:
        print("owner classification refresh skipped: GITHUB_TOKEN is unavailable; existing cache retained", file=sys.stderr)
        return False

    old_repos = old_cache.get("repos", {}) if isinstance(old_cache, dict) else {}
    refreshed: dict[str, dict[str, Any]] = {}
    for repo in id_map:
        entry = fetcher(repo, token)
        old_entry = old_repos.get(repo, {})
        if isinstance(old_entry, dict) and isinstance(old_entry.get("repo_id"), int) and old_entry["repo_id"] != entry["repo_id"]:
            raise RuntimeError(f"{repo}: GitHub repository identity does not match the cached repo_id")
        if old_entry.get("owner_type") == "User" and entry["owner_type"] == "Organization":
            raise RuntimeError(f"{repo}: User to Organization transition requires manual confirmation")
        refreshed[repo] = entry
    payload = {"schema_version": SCHEMA_VERSION, "repos": refreshed}
    errors = verify_cache(id_map, payload)
    if errors:
        raise ValueError("; ".join(errors))
    _atomic_write(cache_path, payload)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="validate cache coverage and schema without network access")
    args = parser.parse_args(argv)
    id_map = _read_json(ID_MAP_PATH)
    if args.verify:
        cache = _read_json(CACHE_PATH)
        errors = verify_cache(id_map, cache)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"owner classification cache verified: {len(id_map)} repositories")
        return 0
    # Review 2026-07-10: an explicit refresh that could not refresh must fail loudly —
    # a silent success would let a stale Organization label survive a transfer to a
    # personal account (fail-closed at the seam).
    return 0 if refresh(token=os.environ.get("GITHUB_TOKEN")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
