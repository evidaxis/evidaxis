#!/usr/bin/env python3
"""Evidaxis m3-v2 package-level dependents collector (t2_deps_v2).

Implements the capture mechanics of governance/QUARANTINE-m3-deps-axis-v2-PREREG.md:

  measurand  = UNIQUE DIRECT dependent packages, dedup by (Dependent.System,
               Dependent.Name), across ALL versions of ALL linkage-verified
               packages of a tracked system, on ONE coherent BigQuery snapshot
  primary    = MinimumDepth = 1 AND DependentIsHighestReleaseWithResolution
  diagnostic = any-depth unique dependents (captured alongside, never scored)
  hygiene    = same-system dependents excluded (monorepo self-deps, PREREG §5)

One capture = one upstream `SnapshotAt` (dedup by snapshot, not wall-clock day;
re-reading the same snapshot is idempotent, never a new point). Provenance per
run: snapshot timestamp, query text sha256, BigQuery job id, result row-set
sha256 (PREREG §2).

Transport: the `bq` CLI (already authenticated via gcloud ADC). Standard
library only. Writes data/observations/<date>/deps_v2.jsonl + a manifest.

BLINDNESS GUARD: until the first capture is deliberately committed (the v2
clock starts there), run only --dry-run (query validation, zero data read).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_VERSION = "t2_deps_v2"
PIN_PATH = REPO / "data" / "deps_id_map.json"
DATASET = "bigquery-public-data.deps_dev_v1"

# Cost model (verified 2026-07-16): Dependents is day-partitioned on SnapshotAt
# (one upstream snapshot per partition, ~8e9 rows) and CLUSTERED on the imported
# package's System/Name/Version. Cheap reads therefore require BOTH a
# DATE(SnapshotAt) partition filter AND literal (System, Name) predicates in
# WHERE (a JOIN against an UNNEST CTE defeats cluster block-pruning — the
# 2026-07-16 quota burn). Literal pin pairs are generated per query.
QUERY_TEMPLATE = """\
SELECT
  d.System AS system,
  d.Name AS name,
  FORMAT_TIMESTAMP('%F %T', ANY_VALUE(d.SnapshotAt)) AS snapshot_at,
  COUNT(DISTINCT IF(d.MinimumDepth = 1 AND d.DependentIsHighestReleaseWithResolution,
                    CONCAT(d.Dependent.System, '/', d.Dependent.Name), NULL)) AS unique_direct,
  COUNT(DISTINCT IF(d.DependentIsHighestReleaseWithResolution,
                    CONCAT(d.Dependent.System, '/', d.Dependent.Name), NULL)) AS unique_any_depth
FROM `{dataset}.Dependents` AS d
WHERE DATE(d.SnapshotAt) = '{snapshot_date}'
  AND ({pin_predicates})
  AND NOT (d.Dependent.System = d.System AND d.Dependent.Name IN ({pin_names}))
GROUP BY system, name
ORDER BY system, name
"""

PARTITIONS_QUERY = (
    "SELECT partition_id FROM "
    f"`{DATASET}.INFORMATION_SCHEMA.PARTITIONS` "
    "WHERE table_name='Dependents' AND partition_id != '__NULL__' "
    "ORDER BY partition_id DESC"
)


MAX_BYTES_BILLED = 20 * 10**9  # 20 GB circuit-breaker per query: with cluster
# pruning a pin-filtered partition read is far below this; without it the query
# FAILS instead of burning the daily quota (lesson of 2026-07-16).


def _bq(sql: str, dry_run: bool = False) -> tuple:
    """Run a query via the bq CLI. Returns (rows, job_id). Raises on failure."""
    cmd = ["bq", "query", "--nouse_legacy_sql", "--format=json", "--quiet"]
    if dry_run:
        cmd.append("--dry_run")
    else:
        cmd.append(f"--maximum_bytes_billed={MAX_BYTES_BILLED}")
    proc = subprocess.run(cmd + [sql], capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"bq failed: {proc.stderr.strip()[:400]}")
    if dry_run:
        return [], None
    rows = json.loads(proc.stdout or "[]")
    # job id: bq --format=json does not emit it; fetch the most recent job
    job = subprocess.run(["bq", "ls", "-j", "-n", "1", "--format=json"],
                         capture_output=True, text=True, timeout=60)
    job_id = None
    try:
        job_id = json.loads(job.stdout)[0]["jobReference"]["jobId"]
    except Exception:  # noqa: BLE001 — provenance best-effort, never blocks capture
        pass
    return rows, job_id


def build_query(pins: dict, snapshot_date: str) -> str:
    """snapshot_date: 'YYYY-MM-DD' partition day (one upstream snapshot per day)."""
    pairs = sorted({(p["system"].upper(), p["package"]) for p in pins.values()})
    pin_predicates = "\n       OR ".join(
        f"(d.System = '{s}' AND d.Name = '{n}')" for s, n in pairs)
    pin_names = ", ".join(f"'{n}'" for _, n in pairs)
    return QUERY_TEMPLATE.format(dataset=DATASET, snapshot_date=snapshot_date,
                                 pin_predicates=pin_predicates, pin_names=pin_names)


def baseline_backfill(pins: dict, id_map: dict, before_ts: str) -> int:
    """One-shot capture of the m3-v2h BASELINE series: the 14 most recent distinct
    upstream SnapshotAt values strictly before the superseding record's timestamp.
    Writes to the backfill namespace (reconstructable by anyone from the public
    dataset), never to the live observation days."""
    rows, _ = _bq(PARTITIONS_QUERY)
    before_day = before_ts[:10].replace("-", "")
    days = sorted(r["partition_id"] for r in rows if r["partition_id"] < before_day)[-14:]
    snapshots = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in days]
    if len(snapshots) < 14:
        print(f"[{COLLECTOR_VERSION}] only {len(snapshots)} partitions before {before_ts}")
        return 1

    out_dir = REPO / "data/observations/backfill/axis3-deps-v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_records, per_snap_meta = [], []
    for snapshot in snapshots:
        sql = build_query(pins, snapshot)
        rows, job_id = _bq(sql)
        by_pkg = {(r["system"].lower(), r["name"]): r for r in rows}
        # one coherent snapshot per day-partition; actual timestamp from the rows
        snapshot_at = rows[0]["snapshot_at"] if rows else f"{snapshot} 00:00:00"
        captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        matched = 0
        for repo, entity_id in sorted(id_map.items()):
            pin = pins.get(repo)
            if pin is None:
                continue
            row = by_pkg.get((pin["system"], pin["package"]))
            if row:
                matched += 1
            all_records.append({
                "v": "t2_deps_v2_1", "series": "baseline",
                "entity_id": entity_id, "github_repo": repo,
                "captured_at": captured_at, "snapshot_at": snapshot_at,
                "collector_version": COLLECTOR_VERSION,
                "source": "deps.dev via BigQuery bigquery-public-data.deps_dev_v1 (CC-BY 4.0)",
                "signals": {"deps_v2_unique_direct": None if row is None else {
                    "value": int(row["unique_direct"]),
                    "any_depth_diagnostic": int(row["unique_any_depth"]),
                    "package": f"{pin['system']}/{pin['package']}",
                    "reconstructable": "true",
                }},
                "coverage": "matched" if row else "not_in_snapshot",
            })
        per_snap_meta.append({"partition_day": snapshot, "snapshot_at": snapshot_at,
                              "bigquery_job_id": job_id,
                              "query_sha256": hashlib.sha256(sql.encode()).hexdigest(),
                              "matched": matched})
        print(f"[{COLLECTOR_VERSION}] baseline {snapshot} ({snapshot_at}): {matched} matched")

    obs_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in all_records)
    (out_dir / "deps_v2.jsonl").write_text(obs_text)
    (out_dir / "baseline_manifest.json").write_text(json.dumps({
        "collector_version": COLLECTOR_VERSION,
        "series": "baseline",
        "before_ts": before_ts,
        "snapshots": per_snap_meta,
        "observations_sha256": hashlib.sha256(obs_text.encode()).hexdigest(),
        "note": "m3-v2h frozen-panel baseline; reconstructable:true; non-gating for promotion",
    }, indent=2, ensure_ascii=False))
    print(f"[{COLLECTOR_VERSION}] baseline complete: {len(snapshots)} snapshots -> "
          f"{out_dir.relative_to(REPO)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="validate the query only; read NO data (blindness guard)")
    ap.add_argument("--snapshot", help="explicit SnapshotAt (default: latest upstream)")
    ap.add_argument("--baseline-backfill", metavar="BEFORE_TS",
                    help="capture the 14 most recent distinct SnapshotAt values strictly "
                         "before BEFORE_TS into the backfill namespace (m3-v2h baseline; "
                         "governance/AXIS3-DEPS-V2-HYBRID-SUPERSESSION-2026-07-16.md)")
    args = ap.parse_args()

    pins = json.loads(PIN_PATH.read_text())["pins"]
    id_map = json.loads((REPO / "etl/id_map.json").read_text())

    if args.baseline_backfill:
        return baseline_backfill(pins, id_map, args.baseline_backfill)

    if args.snapshot:
        snapshot = args.snapshot  # 'YYYY-MM-DD' partition day
    else:
        rows, _ = _bq(PARTITIONS_QUERY)
        d = max(r["partition_id"] for r in rows)
        snapshot = f"{d[:4]}-{d[4:6]}-{d[6:]}"

    sql = build_query(pins, snapshot)
    sql_sha = hashlib.sha256(sql.encode()).hexdigest()

    if args.dry_run:
        _bq(sql, dry_run=True)
        print(f"[{COLLECTOR_VERSION}] DRY-RUN ok — query valid, "
              f"partition {snapshot}, query_sha256 {sql_sha[:16]}…, pins {len(pins)}")
        return 0

    now = datetime.now(timezone.utc)
    captured_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date = now.strftime("%Y-%m-%d")
    out_dir = REPO / "data/observations" / date
    out_dir.mkdir(parents=True, exist_ok=True)

    # Idempotence: one point per upstream SnapshotAt, ever.
    for manifest in (REPO / "data/observations").glob("*/deps_v2_manifest.json"):
        if json.loads(manifest.read_text()).get("snapshot_at") == snapshot:
            print(f"[{COLLECTOR_VERSION}] snapshot {snapshot} already captured "
                  f"({manifest.parent.name}) — idempotent no-op")
            return 0

    rows, job_id = _bq(sql)
    by_pkg = {(r["system"].lower(), r["name"]): r for r in rows}

    records = []
    counts = {"matched": 0, "not_in_snapshot": 0, "no_pin": 0}
    for repo, entity_id in sorted(id_map.items()):
        pin = pins.get(repo)
        if pin is None:
            counts["no_pin"] += 1
            continue
        row = by_pkg.get((pin["system"], pin["package"]))
        coverage = "matched" if row else "not_in_snapshot"
        counts[coverage] += 1
        records.append({
            "v": "t2_deps_v2_1",
            "entity_id": entity_id,
            "github_repo": repo,
            "captured_at": captured_at,
            "snapshot_at": snapshot,
            "collector_version": COLLECTOR_VERSION,
            "source": "deps.dev via BigQuery bigquery-public-data.deps_dev_v1 (CC-BY 4.0)",
            "signals": {"deps_v2_unique_direct": None if row is None else {
                "value": int(row["unique_direct"]),
                "any_depth_diagnostic": int(row["unique_any_depth"]),
                "package": f"{pin['system']}/{pin['package']}",
                "reconstructable": "true",
            }},
            "coverage": coverage,
        })

    obs_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    (out_dir / "deps_v2.jsonl").write_text(obs_text)
    (out_dir / "deps_v2_manifest.json").write_text(json.dumps({
        "collector_version": COLLECTOR_VERSION,
        "captured_at": captured_at,
        "snapshot_at": snapshot,
        "query_sha256": sql_sha,
        "bigquery_job_id": job_id,
        "observations_sha256": hashlib.sha256(obs_text.encode()).hexdigest(),
        "entity_count": len(records),
        **counts,
    }, indent=2, ensure_ascii=False))
    print(f"[{COLLECTOR_VERSION}] snapshot {snapshot}: {counts['matched']} matched, "
          f"{counts['not_in_snapshot']} not-in-snapshot, {counts['no_pin']} unpinned repos "
          f"@ {captured_at} (job {job_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
