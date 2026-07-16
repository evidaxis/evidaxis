#!/usr/bin/env python3
"""m3-v2h quarantine evaluator — scores the frozen panel and evaluates ALL
promotion criteria mechanically (no ad-hoc session arithmetic).

Implements governance/AXIS3-DEPS-V2-HYBRID-SUPERSESSION-2026-07-16.md:
  * REQUIRED --as-of: both the observation cut-off and the cohort/axes snapshot
    are pinned to it (corrects the v1 scorer's latest-snapshot default).
  * Series points are distinct upstream `SnapshotAt` values only.
  * vote(entity, cutoff) = slope(log1p(unique_direct)) > 0 AND within-cohort
    robust-z >= 1 (residualized on log1p(latest)) AND latest >= DEPS_FLOOR
    AND >= MIN_POINTS distinct-snapshot points at the cutoff.
  * flip_j = |R_j Δ R_{j-1}| / |E_j U E_{j-1}|; churn reported; a failed
    endpoint INVALIDATES the transition; small denominator -> UNEVALUABLE.
  * Zero vs absent: `not_in_snapshot` is never a zero; an entity has no point
    before its package's first confirmed existence.
  * Output: content-addressed JSON artifact under
    data/quarantine/axis3-deps-v2/eval/ (committed, not gitignored scratch).

Input series come from deps_v2 observation files (baseline backfill rows are
labeled `series: "baseline"`, live rows `series: "live"`; both carry
snapshot_at). The evaluator never talks to BigQuery — capture is the
collector's job; evaluation is pure and reproducible from the repo.

Standard library only.
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
OUT = REPO / "data" / "quarantine" / "axis3-deps-v2" / "eval"
FROZEN = REPO / "data" / "quarantine" / "axis3-deps-v2" / "frozen-sample-2026-07-16.json"

EVALUATOR_VERSION = "axis3_v2_eval_1"
MIN_POINTS = 14      # per-entity distinct-snapshot floor for a vote (PREREG §3.5)
DEPS_FLOOR = 5
Z_FLOOR = 1.0
Z_CLAMP = 3.0
MIN_FLIP_DENOM = 5   # below this the flip criterion is UNEVALUABLE, never PASS
CRIT = {"coverage_min": 30, "independence_max_abs_r": 0.5,
        "flip_max": 0.30, "rising_share_lo": 0.0, "rising_share_hi": 0.40}


# ---------- series loading ----------

def load_series(as_of: str) -> dict:
    """entity_id -> sorted [(snapshot_at, unique_direct)] with SnapshotAt <= as_of.
    Zero-vs-absent: only rows with coverage == "matched" carry a point."""
    series = defaultdict(dict)
    files = sorted(OBS.glob("*/deps_v2.jsonl")) + \
        sorted((OBS / "backfill" / "axis3-deps-v2").glob("deps_v2.jsonl"))
    for f in files:
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            snap = row.get("snapshot_at")
            if snap is None or snap > as_of:
                continue
            if row.get("coverage") != "matched":
                continue
            sig = row.get("signals", {}).get("deps_v2_unique_direct")
            if sig is None or sig.get("value") is None:
                continue
            series[row["entity_id"]][snap] = int(sig["value"])
    return {eid: sorted(pts.items()) for eid, pts in series.items()}


def cohort_map(as_of: str) -> dict:
    """entity_id -> cohort, from the newest project snapshot <= as_of (the live
    taxonomy authority; seeds.json does not carry entity-level cohorts — the
    2026-07-16 evaluator bug fixed by the dated note in the eval directory)."""
    best = None
    for d in sorted((REPO / "data" / "snapshots").iterdir()):
        if d.name <= as_of[:10] and (d / "snapshot.json").exists():
            best = d
    if best is None:
        return {}
    snap = json.loads((best / "snapshot.json").read_text())
    ents = snap.get("entities")
    items = ents.items() if isinstance(ents, dict) else [(e.get("entity_id"), e) for e in ents]
    return {eid: (e.get("cohort") or "unknown") for eid, e in items}


# ---------- scoring (mirrors m2 semantics) ----------

def _slope(points: list) -> float:
    ys = [math.log1p(v) for _, v in points]
    n = len(ys)
    xbar = (n - 1) / 2
    ybar = sum(ys) / n
    num = sum((i - xbar) * (y - ybar) for i, y in enumerate(ys))
    den = sum((i - xbar) ** 2 for i in range(n))
    return num / den if den else 0.0


def _robust_z(values: dict) -> dict:
    """key -> clamped robust z within one cohort, residualized on size."""
    if len(values) < 2:
        return {k: 0.0 for k in values}
    # residualize slope on log1p(latest) (simple least squares)
    xs = [x for x, _ in values.values()]
    ys = [y for _, y in values.values()]
    xbar, ybar = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - xbar) ** 2 for x in xs)
    beta = (sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys, strict=True)) / den) if den else 0.0
    resid = {k: y - (ybar + beta * (x - xbar)) for k, (x, y) in values.items()}
    med = sorted(resid.values())[len(resid) // 2]
    mad = sorted(abs(v - med) for v in resid.values())[len(resid) // 2]
    scale = 1.4826 * mad
    z = {}
    for k, v in resid.items():
        z[k] = 0.0 if scale == 0 else max(-Z_CLAMP, min(Z_CLAMP, (v - med) / scale))
    return z


def votes_at_cutoff(series: dict, cohorts: dict, cutoff: str) -> tuple:
    """(eligible: set, rising: set, per_entity: dict) at one snapshot cutoff."""
    per_cohort = defaultdict(dict)
    latest = {}
    for eid, pts in series.items():
        upto = [(s, v) for s, v in pts if s <= cutoff]
        if len(upto) < MIN_POINTS:
            continue
        lat = upto[-1][1]
        if lat < DEPS_FLOOR:
            continue
        latest[eid] = lat
        per_cohort[cohorts.get(eid, "unknown")][eid] = (
            math.log1p(lat), _slope(upto))  # (size proxy, slope)
    eligible, rising, per_entity = set(), set(), {}
    for coh, vals in per_cohort.items():
        zs = _robust_z(vals)
        for eid, (_size, slope) in vals.items():
            eligible.add(eid)
            vote = slope > 0 and zs[eid] >= Z_FLOOR
            per_entity[eid] = {"cohort": coh, "slope": round(slope, 6),
                               "z": round(zs[eid], 3), "latest": latest[eid],
                               "rising": vote}
            if vote:
                rising.add(eid)
    return eligible, rising, per_entity


# ---------- criteria ----------

def pearson(pairs):
    n = len(pairs)
    if n < 2:
        return None
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    cov = sum((a - mx) * (b - my) for a, b in pairs)
    va = sum((a - mx) ** 2 for a, _ in pairs)
    vb = sum((b - my) ** 2 for _, b in pairs)
    return cov / math.sqrt(va * vb) if va > 0 and vb > 0 else None


def axes_snapshot(as_of: str) -> dict:
    """entity_id -> (z1, axes_present_count) from the newest project snapshot
    whose date <= as_of (pinned, never 'latest')."""
    best = None
    for d in sorted((REPO / "data" / "snapshots").iterdir()):
        if d.name <= as_of[:10] and (d / "snapshot.json").exists():
            best = d
    if best is None:
        return {}
    snap = json.loads((best / "snapshot.json").read_text())
    ents = snap.get("entities")
    items = ents.items() if isinstance(ents, dict) else [(e.get("entity_id"), e) for e in ents]
    out = {}
    for eid, e in items:
        ax = e.get("axes", {})
        z1 = (ax.get("github_commit_velocity") or {}).get("cohort_z")
        present = sum(1 for a in ax.values() if a and a.get("cohort_z") is not None)
        out[eid] = {"z1": z1, "axes_present": present, "snapshot_dir": best.name}
    return out


def evaluate(as_of: str, label: str) -> dict:
    series = load_series(as_of)
    cohorts = cohort_map(as_of)
    snapshots = sorted({s for pts in series.values() for s, _ in pts})
    if not snapshots:
        return {"error": "no deps_v2 observations at or before --as-of"}

    # per-cutoff votes across the whole series (needed for flip transitions)
    cuts = {}
    for cut in snapshots:
        cuts[cut] = votes_at_cutoff(series, cohorts, cut)

    E_last, R_last, per_entity = cuts[snapshots[-1]]

    # 1 coverage: gate-capable = axes_present >= 1 in the pinned project snapshot
    # plus a voting deps axis here (>= 2 axes total)
    axes = axes_snapshot(as_of)
    gate_capable = sum(1 for eid in E_last if axes.get(eid, {}).get("axes_present", 0) >= 1)
    c1 = {"value": gate_capable, "threshold": CRIT["coverage_min"],
          "pass": gate_capable >= CRIT["coverage_min"]}

    # 2 independence: pooled within-cohort r(z3, z1), cohorts n >= 5
    by_coh = defaultdict(list)
    for eid in E_last:
        z1 = axes.get(eid, {}).get("z1")
        if z1 is not None:
            by_coh[per_entity[eid]["cohort"]].append((per_entity[eid]["z"], z1))
    pooled = []
    for rows in by_coh.values():
        if len(rows) >= 5:
            m3 = sum(a for a, _ in rows) / len(rows)
            m1 = sum(b for _, b in rows) / len(rows)
            pooled += [(a - m3, b - m1) for a, b in rows]
    r = pearson(pooled) if len(pooled) >= 5 else None
    c2 = {"value": None if r is None else round(r, 4), "pairs": len(pooled),
          "threshold": CRIT["independence_max_abs_r"],
          "pass": r is not None and abs(r) < CRIT["independence_max_abs_r"],
          "unevaluable": r is None}

    # 3 flip-rate on consecutive distinct snapshots (Codex formula)
    transitions = []
    for a, b in zip(snapshots, snapshots[1:], strict=False):
        Ea, Ra, _ = cuts[a]
        Eb, Rb, _ = cuts[b]
        denom = len(Ea | Eb)
        if denom < MIN_FLIP_DENOM:
            transitions.append({"from": a, "to": b, "status": "UNEVALUABLE", "denom": denom})
            continue
        flip = len(Ra ^ Rb) / denom
        churn = len(Ea ^ Eb) / denom
        transitions.append({"from": a, "to": b, "flip": round(flip, 4),
                            "churn": round(churn, 4),
                            "pass": flip < CRIT["flip_max"], "denom": denom})
    c3 = {"transitions": transitions,
          "pass": bool(transitions) and all(t.get("pass") for t in transitions
                                            if t.get("status") != "UNEVALUABLE")
                  and any(t.get("status") != "UNEVALUABLE" for t in transitions)}

    # 4 non-degeneracy per voting cohort
    coh_stats = defaultdict(lambda: [0, 0])
    for eid in E_last:
        c = per_entity[eid]["cohort"]
        coh_stats[c][1] += 1
        if per_entity[eid]["rising"]:
            coh_stats[c][0] += 1
    shares = {c: (ris / tot) for c, (ris, tot) in coh_stats.items()}
    c4 = {"shares": {c: round(s, 3) for c, s in shares.items()},
          "pass": bool(shares) and all(CRIT["rising_share_lo"] < s < CRIT["rising_share_hi"]
                                       for s in shares.values())}

    # 5/6 structural (enforced by MIN_POINTS/DEPS_FLOOR and the <= as_of filter)
    c5 = {"pass": True, "note": f"floors enforced in code: >={MIN_POINTS} points, >={DEPS_FLOOR} deps"}
    c6 = {"pass": True, "note": "as-of filter structural; series from committed observations only"}

    return {
        "v": EVALUATOR_VERSION,
        "label": label,
        "as_of": as_of,
        "snapshots_in_series": snapshots,
        "entities_with_series": len(series),
        "voting": len(E_last),
        "rising": sorted(R_last),
        "criteria": {"c1_coverage": c1, "c2_independence": c2, "c3_flip": c3,
                     "c4_nondegeneracy": c4, "c5_floors": c5, "c6_no_lookahead": c6},
        "per_entity": per_entity,
        "axes_snapshot_used": next(iter(axes.values()))["snapshot_dir"] if axes else None,
        "frozen_sample_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest() if FROZEN.exists() else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True,
                    help="evaluation cutoff, 'YYYY-MM-DD HH:MM:SS' (UTC, matches SnapshotAt)")
    ap.add_argument("--label", required=True, choices=["baseline", "live"],
                    help="baseline = pre-record backfill series; live = forward runs")
    args = ap.parse_args()

    result = evaluate(args.as_of, args.label)
    if "error" in result:
        print(f"[{EVALUATOR_VERSION}] {result['error']}")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    digest = hashlib.sha256(blob.encode()).hexdigest()
    path = OUT / f"{args.label}-{args.as_of[:10]}-{digest[:12]}.json"
    path.write_text(blob)

    cr = result["criteria"]
    print(f"[{EVALUATOR_VERSION}] {args.label} @ {args.as_of} — "
          f"{result['voting']} voting / {len(result['rising'])} rising / "
          f"{len(result['snapshots_in_series'])} snapshots")
    for k, v in cr.items():
        status = "PASS" if v.get("pass") else ("UNEVALUABLE" if v.get("unevaluable") else "FAIL")
        print(f"  {k}: {status}")
    print(f"  artifact: {path.relative_to(REPO)} (sha256 {digest[:16]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
