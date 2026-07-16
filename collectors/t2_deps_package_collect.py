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

QUERY_TEMPLATE = """\
WITH pins AS (
  SELECT UPPER(p.system) AS System, p.name AS Name
  FROM UNNEST([
{pin_rows}
  ]) AS p
)
SELECT
  d.System AS system,
  d.Name AS name,
  COUNT(DISTINCT IF(d.MinimumDepth = 1 AND d.DependentIsHighestReleaseWithResolution,
                    CONCAT(d.Dependent.System, '/', d.Dependent.Name), NULL)) AS unique_direct,
  COUNT(DISTINCT IF(d.DependentIsHighestReleaseWithResolution,
                    CONCAT(d.Dependent.System, '/', d.Dependent.Name), NULL)) AS unique_any_depth
FROM `{dataset}.Dependents` AS d
JOIN pins USING (System, Name)
WHERE d.SnapshotAt = TIMESTAMP('{snapshot}')
  AND NOT (d.Dependent.System = d.System AND d.Dependent.Name IN (SELECT Name FROM pins))
GROUP BY system, name
ORDER BY system, name
"""

LATEST_SNAPSHOT_QUERY = (
    "SELECT FORMAT_TIMESTAMP('%F %T', MAX(Time)) AS t "
    f"FROM `{DATASET}.Snapshots`"
)


def _bq(sql: str, dry_run: bool = False) -> tuple:
    """Run a query via the bq CLI. Returns (rows, job_id). Raises on failure."""
    cmd = ["bq", "query", "--nouse_legacy_sql", "--format=json", "--quiet"]
    if dry_run:
        cmd.append("--dry_run")
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


def build_query(pins: dict, snapshot: str) -> str:
    pin_rows = ",\n".join(
        f"    STRUCT('{p['system']}' AS system, '{p['package']}' AS name)"
        for p in sorted(pins.values(), key=lambda x: (x["system"], x["package"]))
    )
    return QUERY_TEMPLATE.format(pin_rows=pin_rows, dataset=DATASET, snapshot=snapshot)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="validate the query only; read NO data (blindness guard)")
    ap.add_argument("--snapshot", help="explicit SnapshotAt (default: latest upstream)")
    args = ap.parse_args()

    pins = json.loads(PIN_PATH.read_text())["pins"]
    id_map = json.loads((REPO / "etl/id_map.json").read_text())

    if args.snapshot:
        snapshot = args.snapshot
    else:
        rows, _ = _bq(LATEST_SNAPSHOT_QUERY)
        snapshot = rows[0]["t"]

    sql = build_query(pins, snapshot)
    sql_sha = hashlib.sha256(sql.encode()).hexdigest()

    if args.dry_run:
        _bq(sql, dry_run=True)
        print(f"[{COLLECTOR_VERSION}] DRY-RUN ok — query valid, 0 bytes read, "
              f"snapshot {snapshot}, query_sha256 {sql_sha[:16]}…, pins {len(pins)}")
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
