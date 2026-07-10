"""counts_check - post-step integrity for snapshot.counts vocabulary (C3).

etl/collect.py is byte-frozen and historically folds D4's ``single-axis`` status
into ``counts.tracked``:

    tracked := status in ("tracked", "single-axis")

That made "tracked" mean two things in one file (entity.status enum vs counts bag).
The presentation layer must use the closed D4 taxonomy
(rising | watch | tracked | single-axis | calibration); the future pipeline must
emit pure ``Counter(entity.status)`` plus a separate ``axis2_present``.

This post-step (stdlib only, outside frozen etl/) enforces the contract on the
LATEST snapshot only:

  * ``counts.entities`` == len(entities)
  * ``counts.axis2_present`` == count of entities with citation axis status
    ``present``
  * status keys match ``Counter(entity.status)`` once the snapshot carries a
    ``single-axis`` key in ``counts`` (honest shape)
  * LEGACY grandfather: if ``single-axis`` is absent from ``counts`` (every
    published snapshot through 2026-07-10), accept the frozen fold
    ``counts.tracked == tracked + single-axis`` while still requiring
    rising / watch / calibration / axis2_present / entities to match

Historical snapshots are not rewritten (append-only archive) and are not
checked by ``--check`` — they stay byte-identical under the grandfather.

Usage:
  python collectors/counts_check.py --check          # CI: latest snapshot only
  python collectors/counts_check.py --date YYYY-MM-DD # check a specific date
  python collectors/counts_check.py --date YYYY-MM-DD --strict  # no legacy fold
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAPSHOTS = REPO / "data" / "snapshots"
LATEST_PTR = REPO / "data" / "latest.json"

# Closed D4 status enum (entity.status). counts may gain keys over time.
STATUS_ENUM = ("rising", "watch", "tracked", "single-axis", "calibration")


def load_latest_date() -> str:
    if LATEST_PTR.is_file():
        return json.loads(LATEST_PTR.read_text(encoding="utf-8"))["snapshot_date"]
    # Fallback: newest dated directory.
    dates = sorted(
        p.name for p in SNAPSHOTS.iterdir()
        if p.is_dir() and (p / "snapshot.json").is_file()
    )
    if not dates:
        raise FileNotFoundError("no snapshots under data/snapshots/")
    return dates[-1]


def expected_counts(entities: list[dict]) -> dict:
    """Pure Counter(status) + entities + axis2_present."""
    statuses = Counter(e.get("status") for e in entities)
    axis2 = sum(
        1
        for e in entities
        if (e.get("axes") or {})
        .get("openalex_citation_momentum", {})
        .get("status")
        == "present"
    )
    out = {
        "entities": len(entities),
        "axis2_present": axis2,
    }
    for s in STATUS_ENUM:
        out[s] = int(statuses.get(s, 0))
    return out


def legacy_fold_counts(entities: list[dict]) -> dict:
    """Frozen collect.py shape: single-axis folded into tracked."""
    pure = expected_counts(entities)
    return {
        "entities": pure["entities"],
        "rising": pure["rising"],
        "watch": pure["watch"],
        "tracked": pure["tracked"] + pure["single-axis"],
        "calibration": pure["calibration"],
        "axis2_present": pure["axis2_present"],
    }


def check_snapshot(snap: dict, *, strict: bool = False) -> list[str]:
    """Return a list of human-readable failure lines (empty = ok)."""
    entities = list(snap.get("entities") or [])
    counts = dict(snap.get("counts") or {})
    pure = expected_counts(entities)
    failures: list[str] = []

    # Always check axis2_present + entities (independent of vocabulary fold).
    for key in ("entities", "axis2_present"):
        got, exp = counts.get(key), pure[key]
        if got != exp:
            failures.append(f"counts.{key}={got} != expected {exp}")

    has_single_axis_key = "single-axis" in counts
    if strict or has_single_axis_key:
        # Honest shape: pure Counter(status) for every enum key.
        for s in STATUS_ENUM:
            got, exp = counts.get(s), pure[s]
            # Absent key is fine only when expected is 0 (optional zero).
            if got is None and exp == 0:
                continue
            if got != exp:
                failures.append(
                    f"counts.{s}={got} != Counter(status)[{s}]={exp} "
                    f"(pure Counter required when single-axis is present or --strict)"
                )
    else:
        # LEGACY grandfather: frozen fold single-axis → tracked.
        leg = legacy_fold_counts(entities)
        for key in ("rising", "watch", "tracked", "calibration"):
            got, exp = counts.get(key), leg[key]
            if got != exp:
                failures.append(
                    f"counts.{key}={got} != legacy expected {exp} "
                    f"(grandfather fold: tracked = tracked + single-axis)"
                )
    return failures


def check_date(date: str, *, strict: bool = False) -> int:
    path = SNAPSHOTS / date / "snapshot.json"
    if not path.is_file():
        print(f"counts_check: no snapshot at {path.relative_to(REPO)}")
        return 1
    snap = json.loads(path.read_text(encoding="utf-8"))
    failures = check_snapshot(snap, strict=strict)
    if failures:
        print(f"counts_check: FAILED for {date}")
        for line in failures:
            print(f"  {line}")
        return 1
    mode = "strict" if strict or ("single-axis" in (snap.get("counts") or {})) else "legacy-fold"
    print(
        f"counts_check: ok {date} "
        f"(entities={len(snap.get('entities') or [])}, mode={mode})"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Assert snapshot.counts matches entity status Counter (+ axis2_present)."
    )
    ap.add_argument(
        "--date",
        default=None,
        help="snapshot date YYYY-MM-DD (default with --check: latest)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="CI mode: check the LATEST snapshot only (historical grandfathered)",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="require pure Counter(status) even without a single-axis counts key",
    )
    args = ap.parse_args()

    if args.check:
        date = args.date or load_latest_date()
        return check_date(date, strict=args.strict)

    if args.date:
        return check_date(args.date, strict=args.strict)

    # Default: same as --check on today's UTC date if present, else latest.
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = SNAPSHOTS / date / "snapshot.json"
    if not path.is_file():
        date = load_latest_date()
    return check_date(date, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
