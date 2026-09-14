"""Count CLEAN forward captures by first-add commit time, never folder date."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from .axis3_inputs import REPO, committed_checks, first_add, git, require_full_history
except ImportError:
    from axis3_inputs import REPO, committed_checks, first_add, git, require_full_history


def forward_count(record: Path, repo: Path = REPO, *, as_of: str | None = None) -> tuple[dict, list[dict]]:
    require_full_history(repo)
    relative = str(record.resolve().relative_to(repo.resolve()))
    commit, recorded_at = first_add(repo, relative)
    checks = committed_checks(repo, as_of)
    if not checks:
        raise ValueError("no committed v2h.1 sanity-check artifacts")
    states = checks[-1]["states"]
    cutoff = datetime.fromisoformat(as_of.replace("Z", "+00:00")) if as_of else None
    rows = []
    for name in git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "data/observations").splitlines():
        match = re.search(r"/deps_v2h1-(\d{4}-\d{2}-\d{2})-manifest\.json$", name)
        if not match:
            continue
        partition = match[1]
        capture_commit, captured_at = first_add(repo, name)
        if cutoff is not None and captured_at > cutoff:
            continue
        clean = states.get(partition) == "CLEAN"
        forward = clean and captured_at > recorded_at
        rows.append({"partition": partition, "capture_commit": capture_commit,
                     "capture_committed_at": captured_at.isoformat(),
                     "state": states.get(partition, "UNKNOWN"), "forward": forward,
                     "reason": "forward CLEAN" if forward else "not CLEAN" if not clean else "captured before record"})
    return {"record": relative, "commit": commit, "committed_at": recorded_at.isoformat()}, sorted(rows, key=lambda r: r["partition"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--as-of", help="optional commit-time cutoff for a frozen historical audit (ISO-8601)")
    args = parser.parse_args()
    try:
        record, rows = forward_count(args.record, as_of=args.as_of)
    except ValueError as exc:
        print(f"axis3_forward_count: {exc}", file=sys.stderr)
        return 1
    print(f"Record {record['record']} first added {record['committed_at']} ({record['commit'][:8]})")
    print("partition   capture commit  capture commit time         state               accounting")
    for row in rows:
        print(f"{row['partition']}  {row['capture_commit'][:8]}        {row['capture_committed_at']}  {row['state']:<18}  {row['reason']}")
    print(f"Forward CLEAN partitions: {sum(r['forward'] for r in rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
