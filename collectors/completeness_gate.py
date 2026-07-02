"""completeness_gate - no entity leaves the published universe silently.

Why: the frozen collector (etl/collect.py) drops an entity from the snapshot
when GitHub /stats/commit_activity stays 202 through all retries - a silent
`continue` with no trace in the manifest. The published 2026-07-01 snapshot
lost 5 of 108 seeded systems this way (including the genesis-tracked Goose),
leaving three mutually inconsistent public universes (seeds 108 / entity cards
107 / snapshot 103). See data/snapshots/2026-07-01/ERRATA.md.

This post-step (outside the byte-frozen etl/) runs right after the collector
in the weekly pipeline and makes any gap explicit:

  * writes dropped.json next to the snapshot: every seeded entity missing from
    snapshot.json, with the reason derivable from the run (202-exhaustion is
    the only silent path in the frozen collector);
  * HARD-FAILS (exit 1) when a previously-tracked entity (one with published
    history) is missing - a series gap must be a loud decision, not drift;
  * a never-before-published seed missing on its first try is reported but
    does not fail the run (its series has not started; retry next week).

Usage:
  python collectors/completeness_gate.py --date YYYY-MM-DD
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(date: str) -> int:
    snap_dir = REPO / "data" / "snapshots" / date
    snap_path = snap_dir / "snapshot.json"
    if not snap_path.exists():
        print(f"completeness_gate: no snapshot at {snap_path.relative_to(REPO)}")
        return 1

    seeds = json.loads((REPO / "etl" / "seeds.json").read_text())
    id_map = json.loads((REPO / "etl" / "id_map.json").read_text())
    seeded = {}
    for vertical in seeds["verticals"].values():
        for e in vertical["entities"]:
            eid = id_map.get(e["github_repo"])
            if eid:
                seeded[eid] = e["github_repo"]

    snap = json.loads(snap_path.read_text())
    present = {e["entity_id"] for e in snap["entities"]}
    missing = {eid: repo for eid, repo in seeded.items() if eid not in present}

    hist_dir = REPO / "data" / "history"
    tracked_missing = {eid: repo for eid, repo in missing.items()
                       if (hist_dir / f"{eid}.jsonl").exists()}
    new_missing = {eid: repo for eid, repo in missing.items() if eid not in tracked_missing}

    report = {
        "v": "dropped_1",
        "snapshot_date": date,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seeded": len(seeded),
        "in_snapshot": len(present),
        "dropped": [
            {"entity_id": eid, "github_repo": repo,
             "previously_tracked": eid in tracked_missing,
             "reason": "collector produced no record for this seeded entity "
                       "(the frozen collector's only silent drop path is "
                       "GitHub stats 202-exhaustion)"}
            for eid, repo in sorted(missing.items())
        ],
        "note": "Written by collectors/completeness_gate.py; a previously-tracked "
                "drop fails the pipeline (series gaps are decisions, not drift).",
    }
    (snap_dir / "dropped.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"completeness_gate: {len(present)}/{len(seeded)} seeded entities in snapshot {date}; "
          f"dropped: {len(missing)} (previously tracked: {len(tracked_missing)}, first-try: {len(new_missing)})")
    for eid, repo in sorted(tracked_missing.items()):
        print(f"  TRACKED ENTITY MISSING: {eid} ({repo}) - series gap!")
    if tracked_missing:
        print("completeness_gate: FAIL - refusing to publish a snapshot that silently "
              "drops previously-tracked entities. Re-run the collector (202 caches warm "
              "on retry) or record a deliberate retirement.")
        return 1
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--date" in args:
        i = args.index("--date")
        if i + 1 < len(args):
            return run(args[i + 1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
