"""Print the m4 axis-3 activation note from committed captures. Thresholds stay put.

Usage: python collectors/axis3_m4_activation_report.py --as-of YYYY-MM-DD
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict

try:
    from . import axis3_m4_identity as identity
    from . import evaluate_axis3_v2h1 as evaluator
    from .axis3_inputs import sanity_as_of
    from .score_m3 import DATA, axis3_records
    from .t2_deps_v2h1_collect import load_panel
except ImportError:
    import axis3_m4_identity as identity
    import evaluate_axis3_v2h1 as evaluator
    from axis3_inputs import sanity_as_of
    from score_m3 import DATA, axis3_records
    from t2_deps_v2h1_collect import load_panel


def _clean(states: dict, as_of: str) -> set[str]:
    return {day for day, status in states.items() if status == "CLEAN" and day <= as_of}


def _canary(series: dict, panel: set, states: dict, snapshot: dict) -> dict:
    kept = {eid: pts for eid, pts in series.items() if eid in panel}
    clean = sorted({day for pts in kept.values() for day, _value in pts
                    if day <= snapshot["snapshot_date"] and states.get(day) == "CLEAN"})
    cohorts = {entity["entity_id"]: entity["cohort"] for entity in snapshot["entities"]}
    _eligible, _rising, per_entity = evaluator.votes_at_cutoff(kept, cohorts, clean)
    return evaluator.canary(per_entity)


def _fmt_agreement(row: dict | None) -> str:
    if not row:
        return "agreement=na n=0"
    return f"agreement={row['agreement']:.3f} n={row['n']}"


def report(as_of: str) -> int:
    snapshot = json.loads((DATA / "snapshots" / as_of / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot["snapshot_date"] != as_of:
        raise ValueError("snapshot directory date differs from payload")
    evidence = sanity_as_of(snapshot["captured_at"])
    states = evidence["states"]
    confirmed = _clean(states, as_of)
    observations = DATA / "observations"
    full, _sha = load_panel()
    m4_panel, _m4_sha = identity.load_panel_m4()
    m3_series = evaluator.load_series(as_of, observations=observations, captured_at=snapshot["captured_at"])
    cases = identity.partition_cases(as_of, observations, snapshot["captured_at"])
    m4_series = identity.derive_m4_series(as_of, observations, snapshot["captured_at"], confirmed=confirmed)
    m3_records, _m3_cut = axis3_records(snapshot, m3_series, states, set(full), {})
    m4_records, m4_cut = axis3_records(snapshot, m4_series, states, set(m4_panel), {})
    names = {entity["entity_id"]: entity.get("name", "") for entity in snapshot["entities"]}
    affected = sorted(eid for eid, pkgs in full.items() if m4_panel.get(eid, set()) != pkgs)
    print(f"axis3 m4 activation as_of={as_of} cutoff={m4_cut} affected={len(affected)}")
    print(
        "thresholds unchanged "
        f"points={evaluator.MIN_POINTS} latest_dependents={evaluator.DEPS_FLOOR} "
        f"rising_z={evaluator.Z_FLOOR} canary_agreement={evaluator.CANARY_AGREEMENT_FLOOR} "
        "canary_n>=3 cohort_minimum=5"
    )
    print("cases count every in-custody partition; usable_run is the confirmed-clean unbroken run")
    status_counts: Counter[str] = Counter()
    for eid in affected:
        counts = Counter(case for _day, case, _value in cases.get(eid, []))
        run = len(m4_series.get(eid, []))
        m4_status = m4_records.get(eid, {}).get("status", "absent")
        m3_status = m3_records.get(eid, {}).get("status", "absent")
        status_counts[m4_status] += 1
        scored = "scored" if m4_status == "scored" else "not_scored"
        print(
            f"{eid} {names.get(eid, '')} cases a={counts['a']} b={counts['b']} c={counts['c']} d={counts['d']} "
            f"usable_run={run} m3_status={m3_status} m4_status={m4_status} {scored}"
        )
    m3_canary = _canary(m3_series, set(full), states, snapshot)
    m4_canary = _canary(m4_series, set(m4_panel), states, snapshot)
    members: Counter[str] = Counter(entity["cohort"] for entity in snapshot["entities"])
    m3_scored: dict[str, int] = defaultdict(int)
    m4_scored: dict[str, int] = defaultdict(int)
    for entity in snapshot["entities"]:
        eid = entity["entity_id"]
        if m3_records[eid]["status"] == "scored":
            m3_scored[entity["cohort"]] += 1
        if m4_records[eid]["status"] == "scored":
            m4_scored[entity["cohort"]] += 1
    print("cohorts m3_vs_m4")
    for cohort in sorted(members):
        print(
            f"cohort {cohort} members={members[cohort]} "
            f"m3_{_fmt_agreement(m3_canary.get(cohort))} m3_scored={m3_scored[cohort]} "
            f"m4_{_fmt_agreement(m4_canary.get(cohort))} m4_scored={m4_scored[cohort]}"
        )
    print("m4_status_counts " + " ".join(f"{key}={status_counts[key]}" for key in sorted(status_counts)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    try:
        return report(args.as_of)
    except (ValueError, OSError, KeyError) as exc:
        print(f"axis3_m4_activation_report: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
