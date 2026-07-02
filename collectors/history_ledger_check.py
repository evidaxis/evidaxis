"""history_ledger_check - every snapshot_id in the public history ledger must
resolve to a published snapshot, or be explicitly superseded.

Why: data/history/*.jsonl is append-only, and the frozen collector appends a
row on EVERY run - including intermediate same-day runs that never get
published. The 2026-07-01 publication day left 79 rows referencing the phantom
snapshot_id 053f31f82bb8 (no such snapshot exists in data/snapshots/), 51 of
them contradicting the published row for the same period. A citing third party
cannot tell which row is canonical.

Forward convention (I5-safe, nothing rewritten):
  * an unpublished run's rows are superseded by APPENDING an amendment row
    (v: ts_amend_1) naming the phantom id and, when one exists, the canonical
    published id for that period;
  * this checker (run by CI) fails when any ts_1 row references a snapshot_id
    that neither resolves to data/snapshots/*/snapshot.json nor is covered by
    an amendment row in the same file.

Usage:
  python collectors/history_ledger_check.py            # verify (exit 1 on unresolved)
  python collectors/history_ledger_check.py --list     # also list offending files
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HISTORY = REPO / "data" / "history"
SNAPSHOTS = REPO / "data" / "snapshots"


def published_ids() -> set:
    ids = set()
    for snap_dir in SNAPSHOTS.iterdir() if SNAPSHOTS.is_dir() else []:
        f = snap_dir / "snapshot.json"
        if f.exists():
            ids.add(json.loads(f.read_text())["snapshot_id"])
    return ids


def check(list_files: bool = False) -> int:
    known = published_ids()
    if not known:
        print("history_ledger_check: no published snapshots found")
        return 1

    unresolved = {}
    files = sorted(HISTORY.glob("*.jsonl")) if HISTORY.is_dir() else []
    for f in files:
        rows = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
        amended = {r.get("supersedes_snapshot_id") for r in rows if r.get("v") == "ts_amend_1"}
        for r in rows:
            if r.get("v") == "ts_amend_1":
                continue
            sid = r.get("snapshot_id")
            if sid and sid not in known and sid not in amended:
                unresolved.setdefault(sid, []).append(f.name)

    if unresolved:
        print(f"history_ledger_check: FAILED - {len(unresolved)} unresolved snapshot_id(s):")
        for sid, names in unresolved.items():
            print(f"  {sid}: {len(names)} file(s)" + (f" e.g. {names[:3]}" if list_files else ""))
        return 1
    print(f"history_ledger_check: OK - {len(files)} history files, "
          f"{len(known)} published snapshot ids, all rows resolve or are amended")
    return 0


if __name__ == "__main__":
    sys.exit(check("--list" in sys.argv[1:]))
