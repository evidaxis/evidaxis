#!/usr/bin/env python3
"""Evidaxis Type-2 deps.dev collector (t2_deps_m1) — the R0 / adoption signal.

For each tracked system, captures the deps.dev DEPENDENT COUNT: how many OTHER
packages depend on it (who BUILDS on it). This is the R0 / transmission signal
consilium-44 (2026-06-30) identified as the *real* signal (vs stars/likes).

  live deps.dev REST  -> point-in-time (TYPE-2, un-backfillable at that granularity)
  BigQuery deps_dev_v1.Dependents (SnapshotAt) -> reconstructable history

Additive: does NOT touch the frozen genesis etl/ nor t2_collect.py (GitHub).
person-free (deps.dev responses are package-level, no persons). Best-effort
repo->package mapping across pypi/npm/cargo; honest null coverage otherwise.

Store: data/observations/{date}/deps.jsonl  + append-only  data/observations/history/{entity_id}.deps.jsonl
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COLLECTOR_VERSION = "t2_deps_m1"
DEPSDEV = "https://api.deps.dev"
SYSTEMS = ("pypi", "npm", "cargo")  # ecosystems deps.dev exposes dependent counts for


def _fetch_json(url: str, tries: int = 3, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": "evidaxis-t2-deps"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.getcode(), resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return 404, None
            if attempt < tries - 1:
                time.sleep(1.5 ** attempt)
                continue
            return exc.code, None
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                time.sleep(1.5 ** attempt)
                continue
            return None, None
    return None, None


def _q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _name_variants(repo: str) -> list[str]:
    n = repo.split("/")[-1].lower()
    return list(dict.fromkeys([n, n.replace("-", ""), n.replace("_", ""), n.replace("-", "_"), n.replace("_", "-")]))


def resolve_dependents(repo: str) -> dict | None:
    """Best-effort: find the package this repo publishes and its default-version dependent count."""
    for system in SYSTEMS:
        for pkg in _name_variants(repo):
            st, body = _fetch_json(f"{DEPSDEV}/v3/systems/{system}/packages/{_q(pkg)}")
            if st != 200 or not body:
                continue
            data = json.loads(body)
            versions = data.get("versions", [])
            if not versions:
                continue
            default = next((v["versionKey"]["version"] for v in versions if v.get("isDefault")), None)
            if not default:
                default = versions[-1]["versionKey"]["version"]
            st2, body2 = _fetch_json(
                f"{DEPSDEV}/v3alpha/systems/{system}/packages/{_q(pkg)}/versions/{_q(default)}:dependents"
            )
            if st2 == 200 and body2:
                dep = json.loads(body2)
                if dep.get("dependentCount") is not None:
                    return {
                        "system": system,
                        "package": pkg,
                        "version": default,
                        "dependent_count": dep.get("dependentCount"),
                        "direct_dependent_count": dep.get("directDependentCount"),
                        "indirect_dependent_count": dep.get("indirectDependentCount"),
                        "response_sha256": hashlib.sha256(body2).hexdigest(),
                    }
    return None


def main() -> int:
    id_map = json.loads((REPO / "etl/id_map.json").read_text())
    seeds = json.loads((REPO / "etl/seeds.json").read_text())
    repos = [e["github_repo"] for v in seeds["verticals"].values() for e in v["entities"]]

    now = datetime.now(timezone.utc)
    captured_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date = now.strftime("%Y-%m-%d")
    iso = now.isocalendar()
    period = f"{iso.year}-w{iso.week:02d}"

    out_dir = REPO / "data/observations" / date
    hist_dir = REPO / "data/observations/history"
    out_dir.mkdir(parents=True, exist_ok=True)
    hist_dir.mkdir(parents=True, exist_ok=True)

    records = []
    matched = 0
    for repo in repos:
        entity_id = id_map.get(repo)
        dep = resolve_dependents(repo)
        signal = None
        if dep:
            matched += 1
            signal = {
                "value": dep["dependent_count"],
                "direct": dep["direct_dependent_count"],
                "indirect": dep["indirect_dependent_count"],
                "source_system": dep["system"],
                "package": dep["package"],
                "version": dep["version"],
                "reconstructable": "partial",
                "method": "deps.dev live REST is point-in-time; BigQuery deps_dev_v1.Dependents (SnapshotAt) has history",
            }
        obs_id = hashlib.sha256(f"{entity_id}|deps_dev_dependents|{captured_at}".encode()).hexdigest()[:16]
        record = {
            "v": "t2_deps_1",
            "observation_id": obs_id,
            "entity_id": entity_id,
            "github_repo": repo,
            "captured_at": captured_at,
            "period": period,
            "collector_version": COLLECTOR_VERSION,
            "source": "deps.dev",
            "endpoint": f"{DEPSDEV}/v3alpha/systems/*/packages/*/versions/*:dependents",
            "response_sha256": dep["response_sha256"] if dep else None,
            "signals": {"deps_dev_dependents": signal},
            "coverage": "matched" if dep else "no_package_match",
            "status": "active",
            "retraction": None,
        }
        records.append(record)
        with (hist_dir / f"{entity_id}.deps.jsonl").open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    obs_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    (out_dir / "deps.jsonl").write_text(obs_text)
    (out_dir / "deps_manifest.json").write_text(json.dumps({
        "collector_version": COLLECTOR_VERSION,
        "captured_at": captured_at,
        "date": date,
        "period": period,
        "entity_count": len(records),
        "matched": matched,
        "unmatched": len(records) - matched,
        "observations_sha256": hashlib.sha256(obs_text.encode()).hexdigest(),
        "signal": "deps_dev_dependents (R0/adoption: how many packages depend on this system)",
        "note": "TYPE-2 point-in-time via live deps.dev REST; additive, NOT scored, person-free.",
    }, indent=2, ensure_ascii=False))

    print(f"[t2_deps_m1] {matched}/{len(records)} systems matched a deps.dev package @ {captured_at} ({period})")
    top = sorted((r for r in records if r["signals"]["deps_dev_dependents"]),
                 key=lambda r: r["signals"]["deps_dev_dependents"]["value"], reverse=True)[:8]
    for r in top:
        s = r["signals"]["deps_dev_dependents"]
        print(f"  {r['github_repo']:<40} {s['value']:>6} dependents ({s['source_system']}:{s['package']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
