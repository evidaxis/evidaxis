"""completeness_gate - no entity leaves the published universe silently.

Why: the frozen collector (etl/collect.py) drops an entity from the snapshot
when GitHub /stats/commit_activity stays 202 through all retries - a silent
`continue` with no trace in the manifest. The published 2026-07-01 snapshot
lost 5 of 108 seeded systems this way (including the genesis-tracked Goose),
leaving three mutually inconsistent public universes (seeds 108 / entity cards
107 / snapshot 103). See data/snapshots/2026-07-01/ERRATA.md.

This post-step (outside the byte-frozen etl/) runs right after the collector
in the weekly pipeline and makes any gap explicit rather than silent:

  * writes dropped.json next to the snapshot: every seeded entity missing from
    snapshot.json, marked previously-tracked or not, as a DECLARED gap;
  * a SMALL transient loss (a few repos whose GitHub /stats/commit_activity is
    still 202 within the collection window) is recorded and the snapshot
    PROCEEDS - a missed week is a permanent hole in the series, worse than a
    handful of declared, visible gaps;
  * a STRUCTURAL loss (> MAX_DROP_FRAC, or zero captured) HARD-FAILS - that is a
    real problem (dead token, mass outage, pipeline break), not GitHub flakiness.

The original bug this guards against was SILENCE (2026-07-01 lost 5/108 with no
trace); the fix is that gaps are always recorded, not that the snapshot is
blocked whenever GitHub's stats endpoint is flaky.

Usage:
  python collectors/completeness_gate.py --date YYYY-MM-DD
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAX_DROP_FRAC = 0.15  # above this the loss is structural (not GitHub /stats flakiness) -> fail


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

    drop_frac = len(missing) / len(seeded) if seeded else 1.0
    report = {
        "v": "dropped_1",
        "snapshot_date": date,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seeded": len(seeded),
        "in_snapshot": len(present),
        "drop_fraction": round(drop_frac, 4),
        "dropped": [
            {"entity_id": eid, "github_repo": repo,
             "previously_tracked": eid in tracked_missing,
             "reason": "not captured this period: the frozen collector produced no record "
                       "(GitHub /stats/commit_activity 202 unresolved within the collection "
                       "window is the dominant transient cause; a genuinely deleted repo 404s). "
                       "A DECLARED gap, not a silent drop."}
            for eid, repo in sorted(missing.items())
        ],
        "note": "Written by collectors/completeness_gate.py. Drops are recorded here "
                "(never silent). The snapshot proceeds for a small transient fraction; "
                "it FAILS only on a structural fraction (see max_drop_fraction).",
        "max_drop_fraction": MAX_DROP_FRAC,
    }
    (snap_dir / "dropped.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"completeness_gate: {len(present)}/{len(seeded)} seeded entities in snapshot {date}; "
          f"dropped: {len(missing)} ({drop_frac:.1%}; previously tracked: {len(tracked_missing)}, "
          f"first-try: {len(new_missing)})")
    for eid, repo in sorted(tracked_missing.items()):
        print(f"  declared gap: {eid} ({repo}) - not captured this period")

    # Structural failure (loud): near-total loss = a real problem (dead token, mass
    # outage, pipeline break), not GitHub's flaky /stats. Refuse to publish.
    if len(present) == 0 or drop_frac > MAX_DROP_FRAC:
        print(f"completeness_gate: FAIL - {len(missing)}/{len(seeded)} dropped "
              f"({drop_frac:.0%} > {MAX_DROP_FRAC:.0%} ceiling) - structural, not transient. "
              "Refusing to publish a gutted snapshot.")
        return 1
    # Small transient loss: recorded in dropped.json as declared gaps; publish. A missed
    # week is a permanent hole in the series and is worse than a handful of declared gaps.
    if tracked_missing:
        print(f"completeness_gate: OK with {len(tracked_missing)} declared gap(s) "
              "(transient, recorded in dropped.json). Snapshot proceeds.")
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
