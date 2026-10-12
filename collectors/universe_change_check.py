#!/usr/bin/env python3
"""universe_change_check - a change to the tracked-system set must be paired with its record.

Why: the candidate-pool denominator is un-backfillable, so ADDING a tracked system
needs a dated discovery-frontier manifest in the same push (the 19->103 loss).
REMOVING one needs either that manifest or a declared departures record
(data/observations/<date>/seed-departures.json, written by the weekly preflight
in collectors/gh_graphql.py) that names every removed repository.

The sets are parsed from both revisions of etl/seeds.json, never inferred from
diff lines (a reformatted file hides additions among removals), and a record
counts only if it exists in the new revision (added or modified, not deleted).

Usage:
  python3 collectors/universe_change_check.py <before-sha> <after-sha>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SEEDS = "etl/seeds.json"
FRONTIER_GLOB = "data/observations/*/discovery-frontier*"
DEPARTURES_GLOB = "data/observations/*/seed-departures.json"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def tracked(repo: Path, rev: str) -> set[str]:
    try:
        raw = _git(repo, "show", f"{rev}:{SEEDS}")
    except subprocess.CalledProcessError:
        return set()
    seeds = json.loads(raw)
    return {e["github_repo"].lower() for v in seeds["verticals"].values() for e in v["entities"]}


def present_records(repo: Path, before: str, after: str, pattern: str) -> list[str]:
    """Paths matching `pattern` that this push added or modified (deleted ones do not pair)."""
    out = _git(repo, "diff", "--name-only", "--diff-filter=AM", before, after, "--", pattern)
    return [p for p in out.splitlines() if p]


def departed_in(repo: Path, rev: str, paths: list[str]) -> set[str]:
    names: set[str] = set()
    for path in paths:
        record = json.loads(_git(repo, "show", f"{rev}:{path}"))
        names |= {d["github_repo"].lower() for d in record.get("departures", [])}
    return names


def check(repo: Path, before: str, after: str) -> tuple[bool, str]:
    old, new = tracked(repo, before), tracked(repo, after)
    added, removed = sorted(new - old), sorted(old - new)
    if not added and not removed:
        return True, "no tracked-system change in this push (cosmetic seeds edits need no manifest)"
    frontier = present_records(repo, before, after, FRONTIER_GLOB)
    if frontier:
        return True, f"universe change (+{len(added)} / -{len(removed)}) is paired with a frontier manifest: {frontier}"
    if added:
        return False, (f"etl/seeds.json adds {len(added)} tracked system(s) ({', '.join(added[:5])}) WITHOUT a paired "
                       "discovery-frontier manifest - the candidate-pool denominator would be lost forever. "
                       "Run collectors/frontier_manifest.py in the same push.")
    records = present_records(repo, before, after, DEPARTURES_GLOB)
    undeclared = sorted(set(removed) - departed_in(repo, after, records))
    if undeclared:
        return False, (f"etl/seeds.json removes {len(undeclared)} tracked system(s) not declared in a seed-departures "
                       f"record or frontier manifest of this push: {', '.join(undeclared[:5])}")
    return True, f"{len(removed)} tracked system(s) removed, each declared in {records}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    ok, message = check(Path.cwd(), argv[0], argv[1])
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
