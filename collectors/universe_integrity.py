#!/usr/bin/env python3
"""Pair seed additions with a frontier and each removal with a dated departure."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPARTED_PATH = re.compile(r"data/observations/(\d{4}-\d{2}-\d{2})/departed\.json")
DEPARTURE_CODES = {301, 302, 307, 308, 404, 410, 451}


def departure_repos(payload: dict, day: str) -> set[str]:
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("invalid departure date")
    if payload.get("schema_version") != "departed_1" or payload.get("date") != day:
        raise ValueError("departed.json schema/date does not match its directory")
    rows = payload.get("departed")
    if not isinstance(rows, list) or not rows:
        raise ValueError("departed.json must contain departure records")
    repos = set()
    for row in rows:
        repo = row.get("github_repo")
        if (not isinstance(repo, str) or not re.fullmatch(r"[^/\s]+/[^/\s]+", repo)
                or row.get("date") != day
                or type(row.get("github_status")) is not int
                or row["github_status"] not in DEPARTURE_CODES):
            raise ValueError("departure needs date, github_repo and a GitHub departure status")
        if repo.lower() in repos:
            raise ValueError(f"duplicate departure: {repo}")
        repos.add(repo.lower())
    return repos


def seed_set(payload: dict) -> set[str]:
    return {e["github_repo"].lower() for v in payload["verticals"].values() for e in v["entities"]}


def check_range(base: str, head: str, repo: Path = REPO) -> list[str]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=repo, text=True)

    before = seed_set(json.loads(git("show", f"{base}:etl/seeds.json")))
    after = seed_set(json.loads(git("show", f"{head}:etl/seeds.json")))
    changes = [line.split("\t") for line in git(
        "diff", "--no-renames", "--name-status", base, head, "--", "data/observations/"
    ).splitlines()]
    errors = []
    departures: set[str] = set()
    frontier = False
    for status, path in changes:
        if re.fullmatch(r"data/observations/\d{4}-\d{2}-\d{2}/discovery-frontier[^/]*", path) and status == "A":
            frontier = True
        match = DEPARTED_PATH.fullmatch(path)
        if not match:
            continue
        # Old evidence cannot be rewritten or reused to justify a new removal.
        if status != "A":
            errors.append(f"{path}: departure journals are append-only")
            continue
        try:
            departures.update(departure_repos(json.loads(git("show", f"{head}:{path}")), match[1]))
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f"{path}: {exc}")
    if after - before and not frontier:
        errors.append("seed additions WITHOUT a paired discovery-frontier manifest: " + ", ".join(sorted(after - before)))
    missing = before - after - departures
    if missing:
        errors.append("seed removal WITHOUT a paired departed.json record: " + ", ".join(sorted(missing)))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    errors = check_range(args.base, args.head)
    for error in errors:
        print(error)
    if not errors:
        print("seed universe changes have paired evidence")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
