#!/usr/bin/env python3
"""m3-v2h.1 collector — system-level unique direct dependents over the FROZEN
expanded panel, plus sentinel canaries, in ONE partition scan.

Council + keeper-approved mechanics (2026-07-21):
  * Panel = union of (a) the 41 v2h pins carried verbatim and (b) the 614
    deps.dev-eligible packages of expansion-manifest-DRAFT.json (sha256-pinned
    at load). Selection was value-blind (metadata only).
  * Measured unit = the SYSTEM: unique direct dependents are counted over the
    UNION of all the system's packages, dedup by (Dependent.System,
    Dependent.Name), intra-system dependents excluded. A monorepo is one row.
  * SENTINEL CANARIES: a declared list of well-known packages OUTSIDE the
    panel, captured with the same metrics in the same scan (marginal cost ~0 —
    billed bytes are per-partition-scan, not per-predicate). Canaries are
    never scored; they exist to tell "the source is sick" apart from "our
    systems moved". (Keeper directive: use the paid scan fully.)
  * One capture = one upstream SnapshotAt; idempotent per snapshot; provenance
    = query sha256, job id, observations sha256 (as v2h).
  * Baseline mode: capture the N most recent partitions BEFORE a given
    timestamp, then let the data-sanity gate classify them; the superseding
    record's baseline = the 14 most recent CONFIRMED-CLEAN of these (reaching
    deeper than 14 calendar partitions when corrupt ones fall inside — the
    2026-06-11/15 lesson).

Cost note (verified): billed bytes = whole-partition scan (~551 GB, ~$3.44)
regardless of predicate count; the CASE-mapped entity aggregation and canaries
ride the same scan for free. Standard library only.
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
COLLECTOR_VERSION = "t2_deps_v2h1"
DATASET = "bigquery-public-data.deps_dev_v1"
BQ_PROJECT = "evidaxis-analytics"  # neutral: person-free job ids
MAX_BYTES_BILLED = 600 * 10**9     # same circuit breaker as v2h

MANIFEST = REPO / "data/quarantine/axis3-deps-v2/expansion-manifest-DRAFT.json"
LEGACY_PINS = REPO / "data/deps_id_map.json"

# Sentinel canaries — declared, never scored, chosen for fame/stability across
# ecosystems and sizes BEFORE any capture (source-health only).
CANARIES = [
    ("PYPI", "numpy"), ("PYPI", "requests"), ("PYPI", "click"), ("PYPI", "rich"),
    ("NPM", "express"), ("NPM", "lodash"), ("NPM", "axios"),
    ("CARGO", "serde"), ("CARGO", "tokio"), ("CARGO", "rand"),
    ("GO", "github.com/spf13/cobra"), ("GO", "github.com/stretchr/testify"),
]

QUERY_HEADER = """\
SELECT
  entity_key,
  FORMAT_TIMESTAMP('%F %T', ANY_VALUE(d.SnapshotAt)) AS snapshot_at,
  COUNT(DISTINCT IF(d.MinimumDepth = 1 AND d.DependentIsHighestReleaseWithResolution,
                    CONCAT(d.Dependent.System, '/', d.Dependent.Name), NULL)) AS unique_direct,
  COUNT(DISTINCT IF(d.DependentIsHighestReleaseWithResolution,
                    CONCAT(d.Dependent.System, '/', d.Dependent.Name), NULL)) AS unique_any_depth,
  COUNT(DISTINCT CONCAT(d.System, '/', d.Name)) AS packages_present
FROM `{dataset}.Dependents` AS d
CROSS JOIN UNNEST([{case_expr}]) AS entity_key
WHERE DATE(d.SnapshotAt) = '{snapshot_date}'
  AND entity_key IS NOT NULL
  AND NOT (CONCAT(d.Dependent.System, '/', d.Dependent.Name) IN UNNEST({self_names}))
GROUP BY entity_key
ORDER BY entity_key
"""


def load_panel() -> tuple:
    """-> (entity_pkgs: entity_id -> set[(SYS, name)], manifest_sha256)."""
    raw = MANIFEST.read_bytes()
    manifest_sha = hashlib.sha256(raw).hexdigest()
    m = json.loads(raw)
    entity_pkgs: dict[str, set] = {}
    for _repo, info in m["repos"].items():
        eid = info.get("entity_id")
        for p in info.get("declared_packages", []):
            if p.get("depsdev_exists"):
                entity_pkgs.setdefault(eid, set()).add(
                    (p["system"].upper(), p["package"]))
    legacy = json.loads(LEGACY_PINS.read_text())["pins"]
    id_map = json.loads((REPO / "etl/id_map.json").read_text())
    for repo, pin in legacy.items():
        eid = id_map.get(repo)
        if eid:
            entity_pkgs.setdefault(eid, set()).add(
                (pin["system"].upper(), pin["package"]))
    return entity_pkgs, manifest_sha


def build_query(entity_pkgs: dict, snapshot_date: str) -> str:
    """One scan: CASE maps each panel package to its entity; canaries map to
    CANARY:<sys>/<name>; everything else -> NULL (dropped)."""
    branches = []
    self_names = set()
    for eid in sorted(entity_pkgs):
        for sys_, name in sorted(entity_pkgs[eid]):
            branches.append(
                f"WHEN d.System = '{sys_}' AND d.Name = '{name}' THEN '{eid}'")
            self_names.add(f"{sys_}/{name}")
    for sys_, name in CANARIES:
        branches.append(
            f"WHEN d.System = '{sys_}' AND d.Name = '{name}' THEN 'CANARY:{sys_}/{name}'")
    case_expr = "CASE " + "\n       ".join(branches) + " ELSE NULL END"
    self_arr = "[" + ", ".join(f"'{n}'" for n in sorted(self_names)) + "]"
    return QUERY_HEADER.format(dataset=DATASET, snapshot_date=snapshot_date,
                               case_expr=case_expr, self_names=self_arr)


def _bq(sql: str, dry_run: bool = False) -> tuple:
    cmd = ["bq", f"--project_id={BQ_PROJECT}", "query",
           "--nouse_legacy_sql", "--format=json", "--quiet", "--max_rows", "10000"]
    if dry_run:
        cmd.append("--dry_run")
    else:
        cmd.append(f"--maximum_bytes_billed={MAX_BYTES_BILLED}")
    proc = subprocess.run([*cmd, sql], capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"bq failed: {proc.stderr.strip()[:400]}")
    if dry_run:
        return [], None
    rows = json.loads(proc.stdout or "[]")
    job = subprocess.run(["bq", f"--project_id={BQ_PROJECT}", "ls", "-j", "-n", "1",
                          "--format=json"], capture_output=True, text=True, timeout=60)
    job_id = None
    try:
        job_id = json.loads(job.stdout)[0]["jobReference"]["jobId"]
    except Exception:
        pass
    return rows, job_id


def partitions_before(ts: str, n: int) -> list:
    rows, _ = _bq(
        f"SELECT partition_id FROM `{DATASET}.INFORMATION_SCHEMA.PARTITIONS` "
        "WHERE table_name='Dependents' AND partition_id != '__NULL__' "
        "ORDER BY partition_id DESC")
    day = ts[:10].replace("-", "")
    days = sorted(r["partition_id"] for r in rows if r["partition_id"] < day)[-n:]
    return [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in days]


def capture_one(entity_pkgs: dict, manifest_sha: str, snapshot: str,
                series: str, out_dir: Path) -> dict:
    sql = build_query(entity_pkgs, snapshot)
    sql_sha = hashlib.sha256(sql.encode()).hexdigest()
    rows, job_id = _bq(sql)
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    by_key = {r["entity_key"]: r for r in rows}
    snapshot_at = rows[0]["snapshot_at"] if rows else f"{snapshot} 00:00:00"
    records, matched = [], 0
    for eid in sorted(entity_pkgs):
        row = by_key.get(eid)
        if row:
            matched += 1
        records.append({
            "v": "t2_deps_v2h1_1", "series": series, "entity_id": eid,
            "captured_at": captured_at, "snapshot_at": snapshot,
            "collector_version": COLLECTOR_VERSION,
            "panel_manifest_sha256": manifest_sha,
            "source": "deps.dev via BigQuery bigquery-public-data.deps_dev_v1 (CC-BY 4.0)",
            "signals": {"deps_v2h1_unique_direct": None if row is None else {
                "value": int(row["unique_direct"]),
                "any_depth_diagnostic": int(row["unique_any_depth"]),
                "packages_present": int(row["packages_present"]),
                "reconstructable": "true"}},
            "coverage": "matched" if row else "not_in_snapshot",
        })
    canaries = {k.split("CANARY:", 1)[1]: {
                    "unique_direct": int(r["unique_direct"]),
                    "unique_any_depth": int(r["unique_any_depth"])}
                for k, r in by_key.items() if k.startswith("CANARY:")}
    out_dir.mkdir(parents=True, exist_ok=True)
    obs_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    (out_dir / f"deps_v2h1-{snapshot}.jsonl").write_text(obs_text)
    meta = {"partition_day": snapshot, "snapshot_at": snapshot_at,
            "series": series, "captured_at": captured_at,
            "bigquery_job_id": job_id, "query_sha256": sql_sha,
            "observations_sha256": hashlib.sha256(obs_text.encode()).hexdigest(),
            "panel_manifest_sha256": manifest_sha,
            "entities": len(records), "matched": matched,
            "canaries": canaries}
    (out_dir / f"deps_v2h1-{snapshot}-manifest.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True))
    print(f"[{COLLECTOR_VERSION}] {series} {snapshot}: {matched}/{len(records)} matched, "
          f"{len(canaries)} canaries (job {job_id})", flush=True)
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot", help="explicit partition day (live capture)")
    ap.add_argument("--baseline-candidates", metavar="BEFORE_TS",
                    help="capture the N most recent partitions before BEFORE_TS "
                         "into the v2h1 backfill namespace (gate classifies them after)")
    ap.add_argument("--n", type=int, default=16,
                    help="candidate count for --baseline-candidates (buffer over 14)")
    args = ap.parse_args()

    entity_pkgs, manifest_sha = load_panel()
    n_pkgs = sum(len(v) for v in entity_pkgs.values())
    print(f"[{COLLECTOR_VERSION}] panel: {len(entity_pkgs)} systems / {n_pkgs} packages "
          f"+ {len(CANARIES)} canaries (manifest {manifest_sha[:12]}…)")

    if args.dry_run:
        snap = args.snapshot or "2026-07-13"
        sql = build_query(entity_pkgs, snap)
        _bq(sql, dry_run=True)
        print(f"[{COLLECTOR_VERSION}] DRY-RUN ok — query valid ({len(sql)//1024} KB), "
              f"partition {snap}")
        return 0

    if args.baseline_candidates:
        snaps = partitions_before(args.baseline_candidates, args.n)
        out_dir = REPO / "data/observations/backfill/axis3-deps-v2h1"
        metas = [capture_one(entity_pkgs, manifest_sha, s, "baseline-candidate", out_dir)
                 for s in snaps]
        (out_dir / "candidates_manifest.json").write_text(json.dumps({
            "collector_version": COLLECTOR_VERSION,
            "before_ts": args.baseline_candidates,
            "candidates": metas,
            "note": "gate classifies these; baseline = 14 most recent CONFIRMED-CLEAN",
        }, indent=2, ensure_ascii=False, sort_keys=True))
        print(f"[{COLLECTOR_VERSION}] {len(metas)} baseline candidates captured -> "
              f"{out_dir.relative_to(REPO)}")
        return 0

    if not args.snapshot:
        rows, _ = _bq(
            f"SELECT MAX(partition_id) AS p FROM `{DATASET}.INFORMATION_SCHEMA.PARTITIONS` "
            "WHERE table_name='Dependents' AND partition_id != '__NULL__'")
        d = rows[0]["p"]
        args.snapshot = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    out_dir = REPO / "data/observations" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # idempotence across all v2h1 manifests
    for mf in (REPO / "data/observations").rglob("deps_v2h1-*-manifest.json"):
        if json.loads(mf.read_text()).get("partition_day") == args.snapshot:
            print(f"[{COLLECTOR_VERSION}] {args.snapshot} already captured "
                  f"({mf.parent}) — idempotent no-op")
            return 0
    capture_one(entity_pkgs, manifest_sha, args.snapshot, "live", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
