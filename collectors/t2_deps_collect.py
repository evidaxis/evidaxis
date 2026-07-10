#!/usr/bin/env python3
"""Evidaxis Type-2 deps.dev collector (t2_deps_m2) — the R0 / adoption signal.

For each tracked system, captures the deps.dev DEPENDENT COUNT: how many OTHER
packages depend on it (who BUILDS on it). This is the R0 / transmission signal
an internal seven-model review (2026-06-30) identified as the *real* signal (vs stars/likes).

  live deps.dev REST  -> point-in-time (TYPE-2, un-backfillable at that granularity)
  BigQuery deps_dev_v1.Dependents (SnapshotAt) -> reconstructable history

m2 hardening (2026-07-02, after a live pypi->npm identity flip on day 2):
  * PACKAGE IDENTITY IS PINNED. First successful resolution freezes
    (system, package) into data/deps_id_map.json; every later capture reads the
    pin ONLY. The series never silently switches ecosystems.
  * OUTAGE != ABSENCE. A non-404 failure is coverage="fetch_error": recorded in
    the daily file for diagnostics but NEVER appended to the long-term history,
    so a deps.dev outage cannot masquerade as "this system has no package".
  * A broken pin (pinned package now 404) is coverage="pin_broken": a loud
    event and a non-zero exit — identity changes are decisions, not drift.
  * Grid resolution (unpinned repos) never concludes "no_package_match" if any
    probe errored; it only concludes absence from clean 404s.

Additive: does NOT touch the frozen genesis etl/ nor t2_collect.py (GitHub).
person-free (deps.dev responses are package-level, no persons).

Store: data/observations/{date}/deps.jsonl + append-only
       data/observations/history/{entity_id}.deps.jsonl (matched/no_package_match only)
Pin registry: data/deps_id_map.json (append-only per repo; a pin is never
rewritten in place — a deliberate identity migration appends a dated note).
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
COLLECTOR_VERSION = "t2_deps_m2"
DEPSDEV = "https://api.deps.dev"
SYSTEMS = ("pypi", "npm", "cargo")  # ecosystems deps.dev exposes dependent counts for
PIN_PATH = REPO / "data" / "deps_id_map.json"
# Total-failure sensor (map#4): if >50% of repos hit fetch_error in one run,
# treat as outage and exit 1. One-bad-repo does not trip (capture-first).
MAX_ERROR_RATE = 0.50


def _fetch_json(url: str, tries: int = 3, timeout: int = 25):
    """Returns (status, body). status=404 means confirmed absence; None means
    network/5xx exhaustion (an OUTAGE, never to be read as absence)."""
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
            return None, None
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


def _load_pins() -> dict:
    if PIN_PATH.exists():
        return json.loads(PIN_PATH.read_text())
    return {"v": "deps_pin_1", "note": "package identity pins: first successful resolution is frozen; "
                                       "a pin is never silently rewritten", "pins": {}}


def _save_pins(pins: dict) -> None:
    pins["pins"] = dict(sorted(pins["pins"].items()))
    PIN_PATH.write_text(json.dumps(pins, indent=2, ensure_ascii=False) + "\n")


def _dependents_for(system: str, pkg: str, version: str) -> tuple:
    """(status, parsed) for the :dependents call. status in {200, 404, None}."""
    st, body = _fetch_json(
        f"{DEPSDEV}/v3alpha/systems/{system}/packages/{_q(pkg)}/versions/{_q(version)}:dependents"
    )
    if st == 200 and body:
        return 200, (json.loads(body), hashlib.sha256(body).hexdigest())
    return st, None


def _default_version(system: str, pkg: str) -> tuple:
    """(status, version|None). status in {200, 404, None}."""
    st, body = _fetch_json(f"{DEPSDEV}/v3/systems/{system}/packages/{_q(pkg)}")
    if st != 200 or not body:
        return st, None
    data = json.loads(body)
    versions = data.get("versions", [])
    if not versions:
        return 404, None
    default = next((v["versionKey"]["version"] for v in versions if v.get("isDefault")), None)
    return 200, default or versions[-1]["versionKey"]["version"]


def _linked_repo_ok(system: str, pkg: str, version: str, github_repo: str) -> tuple:
    """(status, verdict). Does the package's own metadata link back to github_repo?

    A name match alone is NOT identity: 21/81 day-1 name-matches turned out to
    be name-squats or unrelated same-name packages (npm `goose` from 2012 for
    block/goose; `codex` for openai/codex; pypi `alphafold3` squat...). deps.dev
    exposes the declared links on the version record - the package is this
    system's package ONLY if a link points at the system's own repository.
    verdict: True (confirmed) / False (links exist, none match) / None (no
    usable links - unverifiable, treated as no match)."""
    st, body = _fetch_json(f"{DEPSDEV}/v3/systems/{system}/packages/{_q(pkg)}/versions/{_q(version)}")
    if st is None:
        return None, None
    if st != 200 or not body:
        return st, None
    data = json.loads(body)
    links = [l.get("url", "") for l in data.get("links", [])]
    if not links:
        return 200, None
    want = f"github.com/{github_repo}".lower().rstrip("/")
    for url in links:
        u = url.lower().rstrip("/").removesuffix(".git")
        if want in u:
            return 200, True
    return 200, False


def fetch_pinned(pin: dict) -> dict:
    """Capture dependents for a PINNED (system, package). Never falls through."""
    system, pkg = pin["system"], pin["package"]
    st, version = _default_version(system, pkg)
    if st is None:
        return {"coverage": "fetch_error"}
    if st == 404 or version is None:
        return {"coverage": "pin_broken"}
    st2, res = _dependents_for(system, pkg, version)
    if st2 is None:
        return {"coverage": "fetch_error"}
    if st2 != 200:
        return {"coverage": "pin_broken"}
    dep, sha = res
    if dep.get("dependentCount") is None:
        return {"coverage": "pin_broken"}
    return {
        "coverage": "matched",
        "system": system, "package": pkg, "version": version,
        "dependent_count": dep.get("dependentCount"),
        "direct_dependent_count": dep.get("directDependentCount"),
        "indirect_dependent_count": dep.get("indirectDependentCount"),
        "response_sha256": sha,
    }


def resolve_unpinned(repo: str) -> dict:
    """Grid-resolve a repo with NO pin yet. Identity requires BOTH a name match
    AND a source-repo linkage back to the system's repository (name alone
    pinned 21/81 squats/strangers on day 1). Absence may only be concluded
    from clean 404s. Any errored probe ABORTS today's resolution (fetch_error):
    a match found while a higher-priority ecosystem is unreachable could pin
    the WRONG identity (the live pypi->npm flip happened exactly this way)."""
    for system in SYSTEMS:
        for pkg in _name_variants(repo):
            st, version = _default_version(system, pkg)
            if st is None:
                return {"coverage": "fetch_error"}
            if st == 404 or version is None:
                continue
            st_l, linked = _linked_repo_ok(system, pkg, version, repo)
            if st_l is None:
                return {"coverage": "fetch_error"}
            if linked is not True:
                continue  # name-squat / unrelated / unverifiable: NOT this system's package
            st2, res = _dependents_for(system, pkg, version)
            if st2 is None:
                return {"coverage": "fetch_error"}
            if st2 != 200 or res is None:
                continue
            dep, sha = res
            if dep.get("dependentCount") is None:
                continue
            return {
                "coverage": "matched", "newly_pinned": True,
                "system": system, "package": pkg, "version": version,
                "dependent_count": dep.get("dependentCount"),
                "direct_dependent_count": dep.get("directDependentCount"),
                "indirect_dependent_count": dep.get("indirectDependentCount"),
                "response_sha256": sha,
            }
    return {"coverage": "no_package_match"}


def main() -> int:
    id_map = json.loads((REPO / "etl/id_map.json").read_text())
    seeds = json.loads((REPO / "etl/seeds.json").read_text())
    repos = [e["github_repo"] for v in seeds["verticals"].values() for e in v["entities"]]
    pins = _load_pins()

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
    counts = {"matched": 0, "no_package_match": 0, "fetch_error": 0, "pin_broken": 0}
    new_pins = 0
    for repo in repos:
        entity_id = id_map.get(repo)
        if entity_id is None:
            print(f"[{COLLECTOR_VERSION}] WARNING: {repo} has no entity id yet (id_map) - skipped")
            continue
        pin = pins["pins"].get(repo)
        dep = fetch_pinned(pin) if pin else resolve_unpinned(repo)
        coverage = dep["coverage"]
        counts[coverage] += 1
        if dep.pop("newly_pinned", False):
            pins["pins"][repo] = {"system": dep["system"], "package": dep["package"],
                                  "pinned_at": captured_at}
            new_pins += 1

        signal = None
        if coverage == "matched":
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
            "response_sha256": dep.get("response_sha256"),
            "signals": {"deps_dev_dependents": signal},
            "coverage": coverage,
            "status": "active",
            "retraction": None,
        }
        records.append(record)
        # OUTAGE != ABSENCE: only real observations (a count, or a clean
        # confirmed absence) enter the long-term series. fetch_error and
        # pin_broken stay in the daily file + manifest for diagnostics.
        if coverage in ("matched", "no_package_match"):
            with (hist_dir / f"{entity_id}.deps.jsonl").open("a") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    if new_pins:
        _save_pins(pins)

    obs_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    (out_dir / "deps.jsonl").write_text(obs_text)
    (out_dir / "deps_manifest.json").write_text(json.dumps({
        "collector_version": COLLECTOR_VERSION,
        "captured_at": captured_at,
        "date": date,
        "period": period,
        "entity_count": len(records),
        "matched": counts["matched"],
        "unmatched": counts["no_package_match"],
        "fetch_errors": counts["fetch_error"],
        "pins_broken": counts["pin_broken"],
        "new_pins": new_pins,
        "observations_sha256": hashlib.sha256(obs_text.encode()).hexdigest(),
        "signal": "deps_dev_dependents (R0/adoption: how many packages depend on this system)",
        "note": "TYPE-2 point-in-time via live deps.dev REST; additive, NOT scored, person-free; "
                "identity pinned in data/deps_id_map.json.",
    }, indent=2, ensure_ascii=False))

    print(f"[{COLLECTOR_VERSION}] {counts['matched']}/{len(records)} matched, "
          f"{counts['no_package_match']} no-package, {counts['fetch_error']} fetch-errors, "
          f"{counts['pin_broken']} broken pins, {new_pins} new pins @ {captured_at} ({period})")
    top = sorted((r for r in records if r["signals"]["deps_dev_dependents"]),
                 key=lambda r: r["signals"]["deps_dev_dependents"]["value"], reverse=True)[:8]
    for r in top:
        s = r["signals"]["deps_dev_dependents"]
        print(f"  {r['github_repo']:<40} {s['value']:>6} dependents ({s['source_system']}:{s['package']})")

    if counts["pin_broken"]:
        print(f"[{COLLECTOR_VERSION}] THREAT: {counts['pin_broken']} pinned package identities no longer "
              "resolve - an identity change is a decision, not drift. Investigate before re-running.")
        return 1
    n = len(records)
    error_rate = counts["fetch_error"] / n if n else 1.0
    if counts["matched"] == 0 and counts["fetch_error"] > 0:
        print(f"[{COLLECTOR_VERSION}] DEGRADED: zero matches with {counts['fetch_error']} fetch errors "
              "(deps.dev outage?) - failing the run so the day is not recorded as absence.")
        return 1
    if error_rate > MAX_ERROR_RATE:
        print(f"[{COLLECTOR_VERSION}] DEGRADED: fetch_error rate {error_rate:.0%} "
              f"> {MAX_ERROR_RATE:.0%} ({counts['fetch_error']}/{n}) - failing the run")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
