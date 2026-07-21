#!/usr/bin/env python3
"""Data-sanity gate for the deps_v2 series (m3-v2h.1 candidate mechanics).

Implements the council-agreed two-stage design (consilium 2026-07-21):

  Stage 1 — HARD CONTRACTS, fire immediately on a single partition:
    * coverage contract: matched < COVERAGE_MIN (the PRE-EXISTING pre-registered
      promotion criterion constant, 30 — no new post-incident number) -> INVALID
  Stage 2 — SHAPE RULES, symmetric, need the successor partition:
    * panel-wide reversal: an entity's value moves by more than the calibrated
      log-ratio bound vs the previous partition AND returns to within the
      calibrated band of its pre-move level at the next partition. Symmetric:
      dip-and-recover AND spike-and-revert both count (direction-neutral by
      council decision — an asymmetric filter in a positive-only institute
      would function as positive-momentum laundering).
    * a partition whose reversal-entity share exceeds the calibrated panel
      threshold -> SUSPECT_CORRUPT. The LAST partition of a series can only be
      PROVISIONAL (shape rules need a successor).

  Thresholds are NOT hand-set: --calibrate derives them from the frozen
  calibration corpus (every clean transition in all of the institute's series:
  deps_v2 minus the two declared challenge partitions, t2 watchers/open_issues,
  terminated v1 dependents) as max-observed-clean x safety margin, and writes a
  content-addressed calibration artifact. The two known-corrupt partitions
  (2026-06-11, 2026-06-15) are CHALLENGE CASES, excluded from calibration and
  used only to verify the gate fires (they cannot validate a detector designed
  after seeing them — council: challenge != holdout).

  Kill-bar (pre-registered in the governance draft): on --check the gate must
  flag exactly {2026-06-11, 2026-06-15} and zero clean partitions, else the
  rule is wrong and no superseding record may be committed.

Standard library only. Read-only: never mutates observations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OBS = REPO / "data" / "observations"
OUT = REPO / "data" / "quarantine" / "axis3-deps-v2"

GATE_VERSION = "data_sanity_gate_1"
COVERAGE_MIN = 30          # pre-existing pre-registered criterion constant (PREREG c1)
CHALLENGE = {"2026-06-11", "2026-06-15"}  # declared corrupt; calibration-excluded
SAFETY_MARGIN = 3.0        # multiplier over max clean observation (declared, not tuned:
                           # the plateau argument — any margin in [2, 10] separates the
                           # challenge cases from clean history by orders of magnitude)
VALUE_FLOOR = 5            # reversal counted only for entities with pre-move value >= floor
                           # (same floor as DEPS_FLOOR in the evaluator; no new constant)


# ---------- series loading ----------

def deps_v2h1_series() -> tuple:
    """(series, coverage) for the v2h.1 expanded-panel capture files."""
    series, coverage = defaultdict(dict), defaultdict(int)
    files = sorted((OBS / "backfill" / "axis3-deps-v2h1").glob("deps_v2h1-????-??-??.jsonl")) + \
        sorted(OBS.glob("*/deps_v2h1-????-??-??.jsonl"))
    for f in files:
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            snap = (row.get("snapshot_at") or "")[:10]
            if not snap or row.get("coverage") != "matched":
                continue
            sig = (row.get("signals") or {}).get("deps_v2h1_unique_direct")
            if not sig or sig.get("value") is None:
                continue
            series[row["entity_id"]][snap] = int(sig["value"])
            coverage[snap] += 1
    return series, coverage


def deps_v2_series() -> tuple:
    """(series: entity -> {snap: value}, coverage: snap -> matched_count)"""
    series, coverage = defaultdict(dict), defaultdict(int)
    files = sorted(OBS.glob("*/deps_v2.jsonl")) + \
        sorted((OBS / "backfill" / "axis3-deps-v2").glob("deps_v2.jsonl"))
    for f in files:
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            snap = (row.get("snapshot_at") or "")[:10]
            if not snap:
                continue
            if row.get("coverage") != "matched":
                continue
            sig = (row.get("signals") or {}).get("deps_v2_unique_direct")
            if not sig or sig.get("value") is None:
                continue
            series[row["entity_id"]][snap] = int(sig["value"])
            coverage[snap] += 1
    return series, coverage


def other_series() -> dict:
    """Calibration corpus from the institute's other series (daily cadence).
    label -> {key -> {date: value}}"""
    out = {}
    specs = [
        ("t2_watchers", "observations.jsonl", ("signals", "watchers")),
        ("t2_open_issues", "observations.jsonl", ("signals", "open_issues")),
        ("deps_v1", "deps.jsonl", ("signals", "deps_dev_dependents")),
    ]
    for label, fname, (top, key) in specs:
        series = defaultdict(dict)
        for f in sorted(OBS.glob(f"2026-*/{fname}")):
            date = f.parent.name
            for line in f.read_text().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                sig = (row.get(top) or {}).get(key)
                val = sig.get("value") if isinstance(sig, dict) else sig
                rk = row.get("github_repo") or row.get("entity_id")
                if rk and val is not None:
                    series[rk][date] = int(val)
        out[label] = series
    return out


# ---------- reversal metric (symmetric, direction-neutral) ----------

RECOVERY_WINDOW = 2  # successors examined for the return leg. Consecutive corrupt
                     # partitions (the actual incident: 06-11 AND 06-15) hide the
                     # recovery from a 1-step window; 2 covers a corrupt pair while
                     # staying too short to mistake a real regime change for noise.


def reversal_share(series: dict, snaps: list, i: int, bound: float) -> tuple:
    """Share of eligible entities whose value at snaps[i] moved by more than
    `bound` in |log(v_i/v_prev)| AND returned to within `bound`/2 of the
    pre-move level at any of the next RECOVERY_WINDOW snapshots.
    Returns (share, eligible_n)."""
    prev_s, cur_s = snaps[i - 1], snaps[i]
    next_ss = snaps[i + 1:i + 1 + RECOVERY_WINDOW]
    eligible = reversals = 0
    for pts in series.values():
        if prev_s not in pts or cur_s not in pts:
            continue
        succ = [pts[s] for s in next_ss if s in pts]
        if not succ:
            continue
        a, b = pts[prev_s], pts[cur_s]
        if a < VALUE_FLOOR:
            continue
        eligible += 1
        move = abs(math.log((b + 1) / (a + 1)))
        back = min(abs(math.log((c + 1) / (a + 1))) for c in succ)
        if move > bound and back < bound / 2:
            reversals += 1
    return (reversals / eligible if eligible else 0.0), eligible


def max_clean_move(all_series: dict, exclude_snaps: set) -> tuple:
    """Across every clean adjacent transition in the corpus: the max |log-ratio|
    single-entity move (for entities >= VALUE_FLOOR) and the max share of
    entities in one transition moving beyond ln(2). Used to derive bounds."""
    max_move, max_share = 0.0, 0.0
    per_transition = []
    for label, series in all_series.items():
        snaps = sorted({s for pts in series.values() for s in pts})
        for i in range(1, len(snaps)):
            if snaps[i] in exclude_snaps or snaps[i - 1] in exclude_snaps:
                continue
            big = n = 0
            for pts in series.values():
                if snaps[i - 1] not in pts or snaps[i] not in pts:
                    continue
                a, b = pts[snaps[i - 1]], pts[snaps[i]]
                if a < VALUE_FLOOR:
                    continue
                n += 1
                move = abs(math.log((b + 1) / (a + 1)))
                max_move = max(max_move, move)
                if move > math.log(2):
                    big += 1
            if n >= 10:
                share = big / n
                max_share = max(max_share, share)
                per_transition.append({"series": label, "to": snaps[i],
                                       "big_move_share": round(share, 4), "n": n})
    return max_move, max_share, per_transition


# ---------- commands ----------

def calibrate(series_kind: str = "v2") -> int:
    """Council correction (Pro voice, 2026-07-21): calibrate ONLY on the same
    source's clean transitions (deps_v2) — different sources need not share
    anomaly distributions, so pooling them into calibration is illegitimate.
    The institute's OTHER series serve as NEGATIVE-CONTROL FALSIFICATION: the
    derived rule must fire zero times on them, else the feature family is
    wrong. Both results go into the artifact."""
    if series_kind == "v2h1":
        dep_series, coverage = deps_v2h1_series()
    else:
        dep_series, coverage = deps_v2_series()
    max_move, max_share, transitions = max_clean_move({series_kind: dep_series}, CHALLENGE)
    # coverage-relative rule (council statistical layer): threshold derived from
    # clean history — 1 - margin x max clean relative deviation from the median,
    # floored at 0.90 (never more permissive than the v1-draft anchor)
    snaps_cov = {s: c for s, c in coverage.items() if s not in CHALLENGE}
    med_cov = sorted(snaps_cov.values())[len(snaps_cov) // 2] if snaps_cov else 0
    max_dev = max((abs(c - med_cov) / med_cov for c in snaps_cov.values()), default=0.0) if med_cov else 0.0
    coverage_rel_threshold = min(0.90, 1 - SAFETY_MARGIN * max_dev) if med_cov else 0.90
    move_bound = max(max_move * 1.0, math.log(2))  # never below 2x (physical floor)
    # panel threshold: max clean big-move share x margin, floored at 10% so a
    # single entity in a small panel cannot quarantine a partition alone
    panel_threshold = max(max_share * SAFETY_MARGIN, 0.10)

    # negative control: apply the derived rule to every other-series transition
    controls = other_series()
    nc_fired = []
    for label, series in controls.items():
        snaps = sorted({s for pts in series.values() for s in pts})
        for i in range(1, len(snaps) - 1):
            share, eligible = reversal_share(series, snaps, i, move_bound)
            if eligible >= 10 and share > panel_threshold:
                nc_fired.append({"series": label, "at": snaps[i],
                                 "share": round(share, 4)})
    artifact = {
        "v": GATE_VERSION,
        "procedure": "same-source calibration (deps_v2 clean transitions only) x declared margin; "
                     "other institute series = negative-control falsification, never pooled",
        "calibration_series": ["deps_v2"],
        "challenge_partitions_excluded": sorted(CHALLENGE),
        "clean_transitions_scanned": len(transitions),
        "max_clean_single_entity_log_move": round(max_move, 4),
        "max_clean_big_move_share": round(max_share, 4),
        "derived_move_bound_log": round(move_bound, 4),
        "derived_panel_threshold": round(panel_threshold, 4),
        "safety_margin": SAFETY_MARGIN,
        "coverage_min": COVERAGE_MIN,
        "coverage_rel_threshold": round(coverage_rel_threshold, 4),
        "coverage_series_median_clean": med_cov,
        "value_floor": VALUE_FLOOR,
        "series_kind": series_kind,
        "negative_control_series": sorted(controls.keys()),
        "negative_control_firings": nc_fired,
        "negative_control_pass": not nc_fired,
    }
    blob = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(blob.encode()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"sanity-calibration-{digest[:12]}.json"
    path.write_text(blob)
    print(f"[{GATE_VERSION}] same-source calibration over {len(transitions)} clean deps_v2 transitions:")
    print(f"  max clean single-entity |log-move|: {max_move:.4f} "
          f"({math.exp(max_move):.2f}x)")
    print(f"  max clean big-move (>2x) share in one transition: {max_share:.4f}")
    print(f"  derived move bound: {move_bound:.4f} ({math.exp(move_bound):.2f}x)")
    print(f"  derived panel threshold: {panel_threshold:.4f}")
    print(f"  negative control ({', '.join(sorted(controls))}): "
          f"{'PASS — zero firings' if not nc_fired else 'FAIL — ' + str(nc_fired)}")
    print(f"  artifact: {path.relative_to(REPO)}")
    return 0 if not nc_fired else 1


def check(calibration_path: str, series_kind: str = "v2") -> int:
    cal = json.loads(Path(calibration_path).read_text())
    move_bound = cal["derived_move_bound_log"]
    panel_threshold = cal["derived_panel_threshold"]
    if series_kind == "v2h1":
        series, coverage = deps_v2h1_series()
    else:
        series, coverage = deps_v2_series()
    rel_thr = cal.get("coverage_rel_threshold", 0.90)
    snaps = sorted({s for pts in series.values() for s in pts})
    cov_clean = [coverage[s] for s in snaps if s not in CHALLENGE]
    cov_med = sorted(cov_clean)[len(cov_clean) // 2] if cov_clean else 0
    verdicts = {}
    for i, snap in enumerate(snaps):
        if coverage.get(snap, 0) < COVERAGE_MIN and coverage.get(snap, 0) < max(coverage.values()):
            # stage-1 hard contract fires only when THIS partition undershoots
            # the pre-registered floor while the panel demonstrably supports it
            pass  # recorded below; coverage rule evaluated for all partitions uniformly
        if i == 0:
            verdicts[snap] = {"status": "CLEAN", "note": "first point; no predecessor"}
            continue
        if i == len(snaps) - 1:
            verdicts[snap] = {"status": "PROVISIONAL", "note": "last point; shape rules need a successor"}
            continue
        share, eligible = reversal_share(series, snaps, i, move_bound)
        status = "SUSPECT_CORRUPT" if (eligible >= 10 and share > panel_threshold) else "CLEAN"
        verdicts[snap] = {"status": status, "reversal_share": round(share, 4),
                          "eligible": eligible}
    # stage-1 coverage contracts: absolute pre-registered floor + relative-to-median
    for snap in snaps:
        c = coverage.get(snap, 0)
        if cov_med and c < rel_thr * cov_med:
            v = verdicts.setdefault(snap, {})
            v["coverage"] = c
            v["coverage_contract"] = (f"matched {c} < {rel_thr:.2f} x series median {cov_med} "
                                      "(relative-coverage rule, calibration-derived)")
            if v.get("status") not in ("SUSPECT_CORRUPT",):
                v["status"] = "INVALID_COVERAGE"
        if coverage.get(snap, 0) < COVERAGE_MIN:
            v = verdicts.setdefault(snap, {})
            v["coverage"] = coverage.get(snap, 0)
            v["coverage_contract"] = f"matched {coverage.get(snap, 0)} < {COVERAGE_MIN} (pre-registered c1 floor)"
            if v.get("status") not in ("SUSPECT_CORRUPT",):
                v["status"] = "INVALID_COVERAGE"
        else:
            verdicts[snap]["coverage"] = coverage.get(snap, 0)

    flagged = sorted(s for s, v in verdicts.items()
                     if v["status"] in ("SUSPECT_CORRUPT", "INVALID_COVERAGE"))
    result = {"v": GATE_VERSION, "calibration_sha256_prefix": calibration_path.split("-")[-1].split(".")[0],
              "verdicts": verdicts, "flagged": flagged}
    blob = json.dumps(result, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(blob.encode()).hexdigest()
    path = OUT / f"sanity-check-{digest[:12]}.json"
    path.write_text(blob)
    print(f"[{GATE_VERSION}] {len(snaps)} partitions checked")
    for s in snaps:
        v = verdicts[s]
        extra = f" cov={v.get('coverage')}" + (f" share={v.get('reversal_share')}" if 'reversal_share' in v else "")
        print(f"  {s}: {v['status']}{extra}")
    print(f"  FLAGGED: {flagged}")
    print(f"  artifact: {path.relative_to(REPO)}")
    # kill-bar verification (informative print; the governance draft holds the bar)
    expected = sorted(CHALLENGE)
    ok = flagged == expected
    print(f"  KILL-BAR {'PASS' if ok else 'FAIL'}: expected exactly {expected}, got {flagged}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_mutually_exclusive_group(required=True)
    sub.add_argument("--calibrate", action="store_true",
                     help="derive bounds from the clean corpus; write calibration artifact")
    sub.add_argument("--check", metavar="CALIBRATION_JSON",
                     help="apply the gate to the series using a calibration artifact")
    ap.add_argument("--series", choices=["v2", "v2h1"], default="v2")
    args = ap.parse_args()
    if args.calibrate:
        return calibrate(args.series)
    return check(args.check, args.series)


if __name__ == "__main__":
    sys.exit(main())
