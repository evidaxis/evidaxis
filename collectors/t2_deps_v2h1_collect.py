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

# Council enrichment (consilium-03, 2026-07-21): the same paid scan now also
# emits, per system AND per package (GROUPING SETS — one scan):
#   * xor_fp_direct — order-independent BIT_XOR of FARM_FINGERPRINTs of the
#     direct-dependent identity set (tamper evidence: catches count-stable
#     content substitution — the 2026-06 failure class);
#   * sketch64 — deterministic bottom-64 fingerprint sketch (approximate
#     week-over-week retention/Jaccard forever, without storing identity sets
#     and without re-scanning possibly-pruned partitions);
#   * eco_top — APPROX_TOP_COUNT of dependent ecosystems (composition shifts).
# Skipping this in a baseline burn = paying for a second baseline later (Codex).
QUERY_HEADER = """\
WITH obs AS (
  SELECT
    entity_key,
    CONCAT(d.System, '/', d.Name) AS pkg,
    d.SnapshotAt AS snapshot_ts,
    CONCAT(d.Dependent.System, '/', d.Dependent.Name) AS dep_key,
    d.Dependent.System AS dep_system,
    (d.MinimumDepth = 1 AND d.DependentIsHighestReleaseWithResolution) AS direct,
    d.DependentIsHighestReleaseWithResolution AS resolved
  FROM `{dataset}.Dependents` AS d
  CROSS JOIN UNNEST([{case_expr}]) AS entity_key
  WHERE DATE(d.SnapshotAt) = '{snapshot_date}'
    AND entity_key IS NOT NULL
    AND NOT (CONCAT(d.Dependent.System, '/', d.Dependent.Name) IN UNNEST({self_names}))
), fps AS (
  SELECT *, IF(direct, FARM_FINGERPRINT(dep_key), NULL) AS fp_direct FROM obs
)
SELECT
  entity_key,
  IFNULL(pkg, '__SYSTEM__') AS pkg_out,
  FORMAT_TIMESTAMP('%F %T', ANY_VALUE(snapshot_ts)) AS snapshot_at,
  COUNT(DISTINCT IF(direct, dep_key, NULL)) AS unique_direct,
  COUNT(DISTINCT IF(resolved, dep_key, NULL)) AS unique_any_depth,
  COUNT(DISTINCT pkg) AS packages_present,
  BIT_XOR(fp_direct) AS xor_fp_direct,
  ARRAY_AGG(DISTINCT fp_direct IGNORE NULLS ORDER BY fp_direct LIMIT 64) AS sketch64,
  APPROX_TOP_COUNT(IF(direct, dep_system, NULL), 8) AS eco_top
FROM fps
GROUP BY GROUPING SETS ((entity_key), (entity_key, pkg))
ORDER BY entity_key, pkg_out
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
    sys_rows = {r["entity_key"]: r for r in rows if r["pkg_out"] == "__SYSTEM__"}
    pkg_rows = [r for r in rows if r["pkg_out"] != "__SYSTEM__"]
    snapshot_at = rows[0]["snapshot_at"] if rows else f"{snapshot} 00:00:00"

    def _sig(row):
        return {
            "value": int(row["unique_direct"]),
            "any_depth_diagnostic": int(row["unique_any_depth"]),
            "packages_present": int(row["packages_present"]),
            "xor_fp_direct": row.get("xor_fp_direct"),
            "sketch64": [int(x) for x in (row.get("sketch64") or [])],
            "eco_top": row.get("eco_top"),
            "reconstructable": "true",
        }

    records, matched = [], 0
    for eid in sorted(entity_pkgs):
        row = sys_rows.get(eid)
        if row:
            matched += 1
        records.append({
            "v": "t2_deps_v2h1_2", "series": series, "entity_id": eid,
            "captured_at": captured_at, "snapshot_at": snapshot,
            "collector_version": COLLECTOR_VERSION,
            "panel_manifest_sha256": manifest_sha,
            "source": "deps.dev via BigQuery bigquery-public-data.deps_dev_v1 (CC-BY 4.0)",
            "signals": {"deps_v2h1_unique_direct": None if row is None else _sig(row)},
            "coverage": "matched" if row else "not_in_snapshot",
        })
    canaries = {k.split("CANARY:", 1)[1]: _sig(r)
                for k, r in sys_rows.items() if k.startswith("CANARY:")}
    if not canaries:
        raise RuntimeError(
            f"zero canaries parsed for {snapshot} — query/parse broken; aborting before "
            "burning more partitions (canary absence is impossible by design)")
    out_dir.mkdir(parents=True, exist_ok=True)
    obs_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    (out_dir / f"deps_v2h1-{snapshot}.jsonl").write_text(obs_text)
    # per-package breakdown: INTERNAL diagnostics (never published per council —
    # package-level churn is an internal explanation for a system observation)
    pkg_text = "".join(json.dumps({
        "entity_key": r["entity_key"], "pkg": r["pkg_out"], "snapshot_at": snapshot,
        "unique_direct": int(r["unique_direct"]),
        "xor_fp_direct": r.get("xor_fp_direct"),
        "sketch64": [int(x) for x in (r.get("sketch64") or [])],
    }, ensure_ascii=False) + "\n" for r in pkg_rows)
    (out_dir / f"deps_v2h1-{snapshot}-packages.jsonl").write_text(pkg_text)
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


def _ceiling_bq(sql: str, ceiling_bytes: int) -> list:
    """Run with a per-query ceiling (council: exceeding = fail, never silent growth)."""
    cmd = ["bq", f"--project_id={BQ_PROJECT}", "query", "--nouse_legacy_sql",
           "--format=json", "--quiet", "--max_rows", "1000000",
           f"--maximum_bytes_billed={ceiling_bytes}"]
    proc = subprocess.run([*cmd, sql], capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"bq failed (ceiling {ceiling_bytes/1e9:.1f}GB): "
                           f"{proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout or "[]")


def sidecar(entity_pkgs: dict, snapshot: str, repos: list, out_dir: Path) -> dict:
    """Weekly near-free companions (consilium-03): PV2P linkage slice (ceiling
    16GB=$0.10), Projects slice (ceiling 1.6GB=$0.01), retention tripwire ($0)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs = sorted({(s, n) for pk in entity_pkgs.values() for s, n in pk})
    pred = " OR ".join(f"(System='{s}' AND Name='{n}')" for s, n in pairs)
    pv2p = _ceiling_bq(
        f"SELECT System, Name, ProjectType, ProjectName, RelationProvenance, RelationType, "
        f"COUNT(*) AS versions "
        f"FROM `{DATASET}.PackageVersionToProject` "
        f"WHERE DATE(SnapshotAt)='{snapshot}' AND ({pred}) "
        f"GROUP BY System, Name, ProjectType, ProjectName, RelationProvenance, RelationType", 16 * 10**9)
    (out_dir / f"pv2p-{snapshot}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in pv2p))
    repo_arr = ", ".join(f"'{r.lower()}'" for r in sorted(set(repos)))
    projects = _ceiling_bq(
        f"SELECT Type, Name, OpenIssuesCount, StarsCount, ForksCount, "
        f"OSSFuzz.LineCount AS fuzz_lines, OSSFuzz.LineCoverCount AS fuzz_cover "
        f"FROM `{DATASET}.Projects` "
        f"WHERE DATE(SnapshotAt)='{snapshot}' AND LOWER(Name) IN ({repo_arr})", 2 * 10**9)
    (out_dir / f"projects-{snapshot}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in projects))
    trip = _ceiling_bq(
        f"SELECT MIN(partition_id) AS earliest, MAX(partition_id) AS latest, "
        f"COUNT(*) AS n, SUM(total_rows) AS rows_total "
        f"FROM `{DATASET}.INFORMATION_SCHEMA.PARTITIONS` "
        f"WHERE table_name='Dependents' AND partition_id != '__NULL__'", 10**9)
    meta = {"pv2p_rows": len(pv2p), "projects_rows": len(projects),
            "retention_tripwire": trip[0] if trip else None}
    print(f"[{COLLECTOR_VERSION}] sidecar {snapshot}: pv2p {len(pv2p)} rows, "
          f"projects {len(projects)} rows, tripwire {meta['retention_tripwire']}")
    return meta


def projects_hoard(repos: list, out_path: Path) -> None:
    """ONE-TIME full-history hoard of Projects narrow columns for our repos
    (218 snapshots; pruning insurance; ceiling 100GB=$0.625)."""
    repo_arr = ", ".join(f"'{r.lower()}'" for r in sorted(set(repos)))
    rows = _ceiling_bq(
        f"SELECT FORMAT_TIMESTAMP('%F', SnapshotAt) AS snap, Name, "
        f"OpenIssuesCount, StarsCount, ForksCount, "
        f"OSSFuzz.LineCount AS fuzz_lines, OSSFuzz.LineCoverCount AS fuzz_cover "
        f"FROM `{DATASET}.Projects` WHERE LOWER(Name) IN ({repo_arr})", 100 * 10**9)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"[{COLLECTOR_VERSION}] projects hoard: {len(rows)} rows -> {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot", help="explicit partition day (live capture)")
    ap.add_argument("--baseline-candidates", metavar="BEFORE_TS",
                    help="capture the N most recent partitions before BEFORE_TS "
                         "into the v2h1 backfill namespace (gate classifies them after)")
    ap.add_argument("--n", type=int, default=16,
                    help="candidate count for --baseline-candidates (buffer over 14)")
    ap.add_argument("--sidecar", metavar="SNAPSHOT",
                    help="weekly companions for one partition day: PV2P slice + "
                         "Projects slice + retention tripwire (~$0.08 ceiling total)")
    ap.add_argument("--projects-hoard", action="store_true",
                    help="ONE-TIME full-history Projects hoard for panel repos "
                         "(ceiling $0.625; council: pruning insurance)")
    args = ap.parse_args()

    entity_pkgs, manifest_sha = load_panel()
    n_pkgs = sum(len(v) for v in entity_pkgs.values())
    print(f"[{COLLECTOR_VERSION}] panel: {len(entity_pkgs)} systems / {n_pkgs} packages "
          f"+ {len(CANARIES)} canaries (manifest {manifest_sha[:12]}…)")

    panel_repos = list(json.loads((REPO / "etl/id_map.json").read_text()).keys())

    if args.sidecar:
        out_dir = REPO / "data/observations" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        sidecar(entity_pkgs, args.sidecar, panel_repos, out_dir)
        return 0

    if args.projects_hoard:
        projects_hoard(panel_repos,
                       REPO / "data/observations/backfill/projects-history/projects-2022-2026.jsonl")
        return 0

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
