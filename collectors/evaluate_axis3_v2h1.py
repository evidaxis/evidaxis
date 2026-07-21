#!/usr/bin/env python3
"""m3-v2h.1 evaluator — typed state machine + verdict-layer canary + one-way
fragility veto. Council-agreed replacement for evaluate_axis3_v2.py (which
stays untouched as the frozen v2h protocol artifact).

Council mechanics implemented (consilium 2026-07-21, 8 voices):
  * STATE MACHINE: captured → integrity-eligible → confirmed-clean →
    computable → PASS/FAIL. This evaluator consumes the data-sanity gate's
    check artifact and computes on the CONFIRMED-CLEAN prefix only. A
    partition flagged INVALID_COVERAGE / SUSPECT_CORRUPT is excluded (and
    listed); the newest partition (PROVISIONAL) is published as diagnostics
    but is NEVER load-bearing: the official cutoff is the newest FINAL-CLEAN
    snapshot (ordinarily t-1).
  * INVALID input yields NOT_EVALUABLE — never "0% rising", never FAIL.
  * VERDICT-LAYER CANARY: per cohort, the share of voting entities whose
    endpoint-to-endpoint direction agrees with their fitted slope sign. Below
    the declared agreement floor → the cohort's verdicts are HELD (canary
    disagreement is never explained away in-line; it stops evaluation).
  * ONE-WAY FRAGILITY VETO: leave-one-partition-out re-votes plus a Theil-Sen
    robust-slope comparator. An entity whose vote flips under any LOO or whose
    robust slope disagrees in sign with OLS is UNSTABLE: it never counts as
    rising (one-way: instability can only withhold a positive, never grant
    one, and never converts a failure into promotion).
  * Anomaly packet: any HOLD/NOT_EVALUABLE artifact carries the numbers that
    triggered it (no narrative labels).

Same scoring semantics as v2h otherwise (slope of log1p, within-cohort robust
z residualized on size, vote = slope>0 AND z>=1 AND floors). Standard library
only; pure function of committed observations + gate artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from itertools import combinations, pairwise
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OBS = REPO / "data" / "observations"
OUT = REPO / "data" / "quarantine" / "axis3-deps-v2" / "eval"

EVALUATOR_VERSION = "axis3_v2h1_eval_1"
MIN_POINTS = 14
DEPS_FLOOR = 5
Z_FLOOR = 1.0
Z_CLAMP = 3.0
MIN_FLIP_DENOM = 5
CANARY_AGREEMENT_FLOOR = 0.8   # declared governance constant (GLM canary; provisional
                               # pending empirical calibration, stated in the record)
CRIT = {"coverage_min": 30, "independence_max_abs_r": 0.5,
        "flip_max": 0.30, "rising_share_lo": 0.0, "rising_share_hi": 0.40}


# ---------- loading ----------

def load_series(as_of: str) -> dict:
    series = defaultdict(dict)
    files = sorted(OBS.glob("*/deps_v2.jsonl")) + \
        sorted((OBS / "backfill" / "axis3-deps-v2").glob("deps_v2.jsonl"))
    for f in files:
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            snap = (row.get("snapshot_at") or "")[:10]
            if not snap or snap > as_of[:10]:
                continue
            if row.get("coverage") != "matched":
                continue
            sig = (row.get("signals") or {}).get("deps_v2_unique_direct")
            if sig is None or sig.get("value") is None:
                continue
            series[row["entity_id"]][snap] = int(sig["value"])
    return {eid: sorted(pts.items()) for eid, pts in series.items()}


def cohort_map(as_of: str) -> dict:
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


def axes_snapshot(as_of: str) -> dict:
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


def partition_states(gate_artifact: Path) -> dict:
    """snapshot(YYYY-MM-DD) -> status from the data-sanity gate check."""
    check = json.loads(gate_artifact.read_text())
    return {snap: v["status"] for snap, v in check["verdicts"].items()}


# ---------- scoring primitives (v2h semantics) ----------

def _ols_slope(ys: list) -> float:
    n = len(ys)
    xbar = (n - 1) / 2
    ybar = sum(ys) / n
    num = sum((i - xbar) * (y - ybar) for i, y in enumerate(ys))
    den = sum((i - xbar) ** 2 for i in range(n))
    return num / den if den else 0.0


def _theil_sen_slope(ys: list) -> float:
    slopes = [(y2 - y1) / (j - i)
              for (i, y1), (j, y2) in combinations(enumerate(ys), 2) if j != i]
    if not slopes:
        return 0.0
    slopes.sort()
    m = len(slopes)
    return slopes[m // 2] if m % 2 else (slopes[m // 2 - 1] + slopes[m // 2]) / 2


def _robust_z(values: dict) -> dict:
    if len(values) < 2:
        return {k: 0.0 for k in values}
    xs = [x for x, _ in values.values()]
    ys = [y for _, y in values.values()]
    xbar, ybar = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - xbar) ** 2 for x in xs)
    beta = (sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys, strict=True)) / den) if den else 0.0
    resid = {k: y - (ybar + beta * (x - xbar)) for k, (x, y) in values.items()}
    med = sorted(resid.values())[len(resid) // 2]
    mad = sorted(abs(v - med) for v in resid.values())[len(resid) // 2]
    scale = 1.4826 * mad
    return {k: (0.0 if scale == 0 else max(-Z_CLAMP, min(Z_CLAMP, (v - med) / scale)))
            for k, v in resid.items()}


def votes_at_cutoff(series: dict, cohorts: dict, clean_snaps: list) -> tuple:
    """Votes using ONLY the given confirmed-clean snapshots (ordered)."""
    allowed = set(clean_snaps)
    per_cohort, latest, logs = defaultdict(dict), {}, {}
    for eid, pts in series.items():
        upto = [(s, v) for s, v in pts if s in allowed]
        if len(upto) < MIN_POINTS:
            continue
        lat = upto[-1][1]
        if lat < DEPS_FLOOR:
            continue
        ys = [math.log1p(v) for _, v in upto]
        latest[eid] = lat
        logs[eid] = (upto, ys)
        per_cohort[cohorts.get(eid, "unknown")][eid] = (math.log1p(lat), _ols_slope(ys))
    eligible, rising, per_entity = set(), set(), {}
    for coh, vals in per_cohort.items():
        zs = _robust_z(vals)
        for eid, (_sz, slope) in vals.items():
            eligible.add(eid)
            upto, ys = logs[eid]
            # one-way fragility veto -----------------------------------------
            robust = _theil_sen_slope(ys)
            sign_disagrees = (slope > 0) != (robust > 0) and not (slope == 0 and robust == 0)
            loo_flips = False
            base_vote = slope > 0 and zs[eid] >= Z_FLOOR
            for k in range(len(ys)):
                loo_ys = ys[:k] + ys[k + 1:]
                if len(loo_ys) < 2:
                    continue
                if (_ols_slope(loo_ys) > 0) != (slope > 0):
                    loo_flips = True
                    break
            unstable = sign_disagrees or loo_flips
            vote = base_vote and not unstable   # instability only withholds
            per_entity[eid] = {
                "cohort": coh, "slope": round(slope, 6),
                "theil_sen": round(robust, 6), "z": round(zs[eid], 3),
                "latest": latest[eid], "points": len(ys),
                "endpoint_up": upto[-1][1] > upto[0][1],
                "unstable": unstable, "rising": vote,
                **({"veto": "one-way fragility (LOO flip or robust-sign disagreement)"}
                   if base_vote and unstable else {}),
            }
            if vote:
                rising.add(eid)
    return eligible, rising, per_entity


def canary(per_entity: dict) -> dict:
    """Per-cohort agreement between slope sign and endpoint direction."""
    stats = defaultdict(lambda: [0, 0])
    for e in per_entity.values():
        agrees = (e["slope"] > 0) == e["endpoint_up"]
        stats[e["cohort"]][0] += agrees
        stats[e["cohort"]][1] += 1
    out = {}
    for coh, (ok, n) in stats.items():
        agreement = ok / n if n else 1.0
        out[coh] = {"agreement": round(agreement, 3), "n": n,
                    "hold": n >= 3 and agreement < CANARY_AGREEMENT_FLOOR}
    return out


# ---------- evaluation ----------

def evaluate(as_of: str, label: str, gate_artifact: Path) -> dict:
    series = load_series(as_of)
    cohorts = cohort_map(as_of)
    states = partition_states(gate_artifact)
    snaps = sorted({s for pts in series.values() for s, _ in pts})
    if not snaps:
        return {"error": "no deps_v2 observations at or before --as-of"}

    excluded = sorted(s for s in snaps if states.get(s) in ("INVALID_COVERAGE", "SUSPECT_CORRUPT"))
    provisional = [s for s in snaps if states.get(s) == "PROVISIONAL"]
    clean = [s for s in snaps if states.get(s, "CLEAN") == "CLEAN"]
    unknown = sorted(s for s in snaps if s not in states)
    if unknown:
        return {"error": f"gate artifact does not cover partitions: {unknown} — refuse to compute (fail closed)"}
    if len(clean) == 0:
        return {"v": EVALUATOR_VERSION, "label": label, "as_of": as_of,
                "status": "NOT_EVALUABLE",
                "anomaly_packet": {"reason": "zero confirmed-clean partitions",
                                   "excluded_partitions": excluded,
                                   "provisional": provisional}}

    # official = confirmed-clean prefix (provisional last point is diagnostics only)
    E, R, per_entity = votes_at_cutoff(series, cohorts, clean)
    can = canary(per_entity)
    held_cohorts = sorted(c for c, v in can.items() if v["hold"])

    axes = axes_snapshot(as_of)
    gate_capable = sum(1 for eid in E if axes.get(eid, {}).get("axes_present", 0) >= 1)
    c1 = {"value": gate_capable, "threshold": CRIT["coverage_min"],
          "pass": gate_capable >= CRIT["coverage_min"]}

    by_coh = defaultdict(list)
    for eid in E:
        z1 = axes.get(eid, {}).get("z1")
        if z1 is not None and per_entity[eid]["cohort"] not in held_cohorts:
            by_coh[per_entity[eid]["cohort"]].append((per_entity[eid]["z"], z1))
    pooled = []
    for rows in by_coh.values():
        if len(rows) >= 5:
            m3 = sum(a for a, _ in rows) / len(rows)
            m1 = sum(b for _, b in rows) / len(rows)
            pooled += [(a - m3, b - m1) for a, b in rows]
    r = None
    if len(pooled) >= 5:
        n = len(pooled)
        mx = sum(a for a, _ in pooled) / n
        my = sum(b for _, b in pooled) / n
        cov = sum((a - mx) * (b - my) for a, b in pooled)
        va = sum((a - mx) ** 2 for a, _ in pooled)
        vb = sum((b - my) ** 2 for _, b in pooled)
        r = cov / math.sqrt(va * vb) if va > 0 and vb > 0 else None
    c2 = {"value": None if r is None else round(r, 4), "pairs": len(pooled),
          "threshold": CRIT["independence_max_abs_r"],
          "pass": r is not None and abs(r) < CRIT["independence_max_abs_r"],
          "unevaluable": r is None}

    transitions = []
    for a, b in pairwise(clean):
        Ea, Ra, _ = votes_at_cutoff(series, cohorts, [s for s in clean if s <= a])
        Eb, Rb, _ = votes_at_cutoff(series, cohorts, [s for s in clean if s <= b])
        denom = len(Ea | Eb)
        if denom < MIN_FLIP_DENOM:
            transitions.append({"from": a, "to": b, "status": "UNEVALUABLE", "denom": denom})
            continue
        transitions.append({"from": a, "to": b,
                            "flip": round(len(Ra ^ Rb) / denom, 4),
                            "churn": round(len(Ea ^ Eb) / denom, 4),
                            "pass": len(Ra ^ Rb) / denom < CRIT["flip_max"], "denom": denom})
    c3 = {"transitions": transitions,
          "pass": bool(transitions) and all(t.get("pass") for t in transitions
                                            if t.get("status") != "UNEVALUABLE")
                  and any(t.get("status") != "UNEVALUABLE" for t in transitions)}

    coh_stats = defaultdict(lambda: [0, 0])
    for eid in E:
        c = per_entity[eid]["cohort"]
        coh_stats[c][1] += 1
        if per_entity[eid]["rising"]:
            coh_stats[c][0] += 1
    shares = {c: ris / tot for c, (ris, tot) in coh_stats.items() if c not in held_cohorts}
    c4 = {"shares": {c: round(s, 3) for c, s in shares.items()},
          "held_cohorts": held_cohorts,
          "pass": bool(shares) and not held_cohorts and
                  all(CRIT["rising_share_lo"] < s < CRIT["rising_share_hi"]
                      for s in shares.values())}

    status = "HOLD" if held_cohorts else "EVALUATED"
    result = {
        "v": EVALUATOR_VERSION,
        "label": label,
        "as_of": as_of,
        "status": status,
        "state_machine": {"confirmed_clean": clean, "provisional": provisional,
                          "excluded_partitions": excluded,
                          "official_cutoff": clean[-1],
                          "gate_artifact": gate_artifact.name},
        "voting": len(E), "rising": sorted(R),
        "unstable_vetoed": sorted(e for e, v in per_entity.items()
                                  if v.get("veto")),
        "canary": can,
        "criteria": {"c1_coverage": c1, "c2_independence": c2, "c3_flip": c3,
                     "c4_nondegeneracy": c4,
                     "c5_floors": {"pass": True,
                                   "note": f">= {MIN_POINTS} clean points, >= {DEPS_FLOOR} deps"},
                     "c6_no_lookahead": {"pass": True,
                                         "note": "as-of + gate-artifact pinned; clean prefix only"}},
        "per_entity": per_entity,
        "axes_snapshot_used": next(iter(axes.values()))["snapshot_dir"] if axes else None,
    }
    if held_cohorts:
        result["anomaly_packet"] = {
            "reason": "verdict-layer canary disagreement",
            "cohorts": {c: can[c] for c in held_cohorts},
            "note": "criteria involving held cohorts are not asserted; no narrative label attached",
        }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--label", required=True, choices=["baseline", "live"])
    ap.add_argument("--gate-check", required=True,
                    help="data_sanity_gate --check artifact (partition states)")
    args = ap.parse_args()
    result = evaluate(args.as_of, args.label, Path(args.gate_check))
    if "error" in result:
        print(f"[{EVALUATOR_VERSION}] {result['error']}")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    digest = hashlib.sha256(blob.encode()).hexdigest()
    path = OUT / f"v2h1-{args.label}-{args.as_of[:10]}-{digest[:12]}.json"
    path.write_text(blob)
    print(f"[{EVALUATOR_VERSION}] {args.label} @ {args.as_of} — status {result['status']} — "
          f"official cutoff {result['state_machine']['official_cutoff']} — "
          f"{result['voting']} voting / {len(result['rising'])} rising "
          f"(vetoed unstable: {len(result['unstable_vetoed'])})")
    for k, v in result["criteria"].items():
        s = "PASS" if v.get("pass") else ("UNEVALUABLE" if v.get("unevaluable") else "FAIL")
        print(f"  {k}: {s}")
    print(f"  artifact: {path.relative_to(REPO)} (sha256 {digest[:16]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
