"""shadow_axis3_deps - QUARANTINE shadow-run of a candidate third axis (deps.dev
dependents momentum), per the renewal protocol's steal-from-science funnel.

STATUS: SHADOW. This is stage 3 (shadow-run) of the quarantine funnel: the
candidate axis is computed IN PARALLEL to the live methodology, on the same
accumulated observations, WITHOUT publication. Nothing here touches data/,
snapshots, scores, or the site. Output goes to shadow-runs/ (gitignored) and
stdout only. Promotion to a scored axis requires the pre-registered A/B
criteria (see the quarantine record) and an explicit human decision, deployed
forward as a new methodology version - never backfilled.

Axis definition mirrored from m2 semantics:
  slope  = least-squares slope of log(1 + dependents) over daily capture points
  z      = within-cohort robust-z (median / 1.4826*MAD, clamped to +/-3),
           residualized on log(1 + latest dependents) as the size proxy
  vote   = slope > 0 AND z >= 1 AND latest dependents >= DEPS_FLOOR (5)
  guard  = no vote until >= MIN_POINTS (14) daily capture points exist

Pure standard library. Read-only over data/.

Usage:
  python collectors/shadow_axis3_deps.py          # run; writes shadow-runs/axis3-deps/<date>.json
  python collectors/shadow_axis3_deps.py --dry    # print summary only, write nothing
"""
import json
import math
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OBS = REPO / "data" / "observations"
SNAPSHOTS = REPO / "data" / "snapshots"
OUT = REPO / "shadow-runs" / "axis3-deps"

MIN_POINTS = 14     # daily capture points required before the axis may vote
DEPS_FLOOR = 5      # latest dependents floor (analog of the m2 activity floor)
Z_FLOOR = 1.0       # mirrors m2 RISING_Z_FLOOR
Z_CLAMP = 3.0


def _load_series():
    """entity_id -> sorted [(date, dependents)] from every daily deps.jsonl.

    Identity guard: points are kept only for the entity's MODAL (system, package)
    identity. A resolver flip (live case: harness-sdk pypi->npm on day 2) would
    otherwise splice two different packages into one series and contaminate the
    pre-registered A/B. Dropped points are counted and reported."""
    raw = {}
    for day_dir in sorted(OBS.iterdir()) if OBS.is_dir() else []:
        f = day_dir / "deps.jsonl"
        if not day_dir.is_dir() or not f.exists():
            continue
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("coverage") != "matched":
                continue
            sig = row.get("signals", {}).get("deps_dev_dependents", {})
            if "value" not in sig:
                continue
            ident = (sig.get("source_system"), sig.get("package"))
            raw.setdefault(row["entity_id"], []).append((day_dir.name, sig["value"], ident))

    # verified pins are the identity ground truth (data/deps_id_map.json);
    # an entity with no verified pin contributes NO points (strict - the A/B
    # must not run on unverifiable series). See data/observations/ERRATA.md.
    pins = {}
    pin_file = REPO / "data" / "deps_id_map.json"
    if pin_file.exists():
        pin_map = json.loads(pin_file.read_text()).get("pins", {})
        id_map = json.loads((REPO / "etl" / "id_map.json").read_text())
        for repo, pin in pin_map.items():
            eid = id_map.get(repo)
            if eid:
                pins[eid] = (pin["system"], pin["package"])

    series, dropped = {}, 0
    for eid, pts in raw.items():
        pin = pins.get(eid)
        if pin is None:
            dropped += len(pts)
            continue
        kept = [(d, v) for d, v, ident in pts if ident == pin]
        dropped += len(pts) - len(kept)
        if kept:
            series[eid] = sorted(kept)
    if dropped:
        print(f"  identity guard: dropped {dropped} point(s) without a verified pin identity")
    return series


def _latest_snapshot():
    dirs = sorted(p for p in SNAPSHOTS.iterdir() if p.is_dir())
    snap = json.loads((dirs[-1] / "snapshot.json").read_text())
    return dirs[-1].name, snap


def _slope(points):
    """Least-squares slope of log(1+value) over day index."""
    n = len(points)
    xs = list(range(n))
    ys = [math.log1p(v) for _, v in points]
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False)) / den


def _robust_z(values):
    """Within-cohort robust z (median/MAD, 1.4826, clamped), m2-style."""
    med = sorted(values)[len(values) // 2]
    mad = sorted(abs(v - med) for v in values)[len(values) // 2]
    scale = 1.4826 * mad
    if scale == 0:
        return [0.0 for _ in values]
    return [max(-Z_CLAMP, min(Z_CLAMP, (v - med) / scale)) for v in values]


def _residualize(zs, sizes):
    """Residualize z on log(1+size) within the cohort (single OLS pass), m2-style."""
    n = len(zs)
    if n < 3:
        return zs
    xs = [math.log1p(s) for s in sizes]
    mx, mz = sum(xs) / n, sum(zs) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return zs
    b = sum((x - mx) * (z - mz) for x, z in zip(xs, zs, strict=False)) / den
    return [max(-Z_CLAMP, min(Z_CLAMP, z - b * (x - mx))) for z, x in zip(zs, xs, strict=False)]


def main() -> int:
    dry = "--dry" in sys.argv[1:]
    series = _load_series()
    snap_date, snap = _latest_snapshot()
    n_days = len({d for pts in series.values() for d, _ in pts})

    entities = {e["entity_id"]: e for e in snap["entities"]}
    cohorts = {}
    for eid, e in entities.items():
        cohorts.setdefault(e.get("cohort", "?"), []).append(eid)

    rows = {}
    for eid, pts in series.items():
        if eid not in entities:
            continue
        latest = pts[-1][1]
        rows[eid] = {
            "entity_id": eid,
            "cohort": entities[eid].get("cohort", "?"),
            "points": len(pts),
            "latest_dependents": latest,
            "slope": _slope(pts) if len(pts) >= MIN_POINTS else None,
            "z": None,
            "vote_rising": False,
            "status": "voting" if len(pts) >= MIN_POINTS else f"accumulating ({len(pts)}/{MIN_POINTS})",
        }

    # within-cohort z over entities whose slope is computable
    for _cohort, eids in cohorts.items():
        voting = [eid for eid in eids if rows.get(eid, {}).get("slope") is not None]
        if len(voting) < 5:            # mirrors MIN_COHORT_FOR_BADGE
            continue
        zs = _robust_z([rows[eid]["slope"] for eid in voting])
        zs = _residualize(zs, [rows[eid]["latest_dependents"] for eid in voting])
        for eid, z in zip(voting, zs, strict=False):
            r = rows[eid]
            r["z"] = round(z, 3)
            r["vote_rising"] = (r["slope"] > 0 and z >= Z_FLOOR
                                and r["latest_dependents"] >= DEPS_FLOOR)

    def _axes_present(e):
        # axis-1 carries no status field (present == slope computed); axis-2 is explicit
        n = 0
        for a in e.get("axes", {}).values():
            status = a.get("status")
            if status == "present" or (status is None and a.get("slope") is not None):
                n += 1
        return n

    covered = len(rows)
    nonzero = sum(1 for r in rows.values() if r["latest_dependents"] > 0)
    votes = sum(1 for r in rows.values() if r["vote_rising"])
    m2_two_axes = sum(1 for e in entities.values() if _axes_present(e) >= 2)
    m3_two_axes = sum(
        1 for eid, e in entities.items()
        if _axes_present(e) + (1 if rows.get(eid, {}).get("slope") is not None else 0) >= 2)

    report = {
        "v": "shadow_axis3_deps_1",
        "run_for_snapshot": snap_date,
        "days_accumulated": n_days,
        "min_points_to_vote": MIN_POINTS,
        "entities_covered": covered,
        "entities_nonzero": nonzero,
        "voting_entities": sum(1 for r in rows.values() if r["status"] == "voting"),
        "rising_votes": votes,
        "gate_capable_m2": m2_two_axes,
        "gate_capable_m3_projected": m3_two_axes,
        "note": "SHADOW quarantine run; not scored, not published, promotion only via "
                "pre-registered A/B criteria + human decision, forward as a new "
                "methodology version.",
        "entities": sorted(rows.values(), key=lambda r: r["entity_id"]),
    }

    print(f"shadow axis-3 (deps.dev dependents momentum) — snapshot {snap_date}")
    print(f"  days accumulated: {n_days} (voting needs {MIN_POINTS})")
    print(f"  coverage: {covered} matched, {nonzero} nonzero")
    print(f"  voting now: {report['voting_entities']}, rising votes: {votes}")
    print(f"  gate-capable: m2={m2_two_axes} -> m3 projected={m3_two_axes}")

    if not dry:
        OUT.mkdir(parents=True, exist_ok=True)
        out = OUT / f"{snap_date}-run-{date.today().isoformat()}.json"
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"  written: {out.relative_to(REPO)} (gitignored; shadow namespace)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
