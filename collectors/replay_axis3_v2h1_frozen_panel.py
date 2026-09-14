#!/usr/bin/env python3
"""Frozen-panel equivalence replay for the m3-v2h.2 verdict (2026-09-14).

Why this exists: the v2h.1 collector built its panel as the sha-pinned manifest
UNION the live pin map, so post-freeze pins entered captures from partition
2026-08-10 (governance/ERRATUM-2026-09-14-v2h1-collector-panel-drift.md). That
has two effects, and an equivalence claim has to cover both:
  1. extra rows for post-freeze systems (undone by filtering to the frozen 90);
  2. extra names in the query's self-dependent exclusion list, which removed any
     post-freeze package from the dependent counts of FROZEN systems. Filtering
     output cannot undo this; it needs the excluded (package, dependent) pairs,
     taken from one read-only BigQuery pull committed in EVIDENCE.
The replay first proves its reconstruction of each capture's panel (the rebuilt
SQL must hash to the query_sha256 the capture manifest recorded, and the pull
must cover every post-freeze name), then restores both effects and re-runs the
COMMITTED sanity-gate and evaluator code unchanged (their loaders are swapped,
nothing else), and compares with the committed artifacts. Variants: FILTER_ONLY
(effect 1 only), EXACT (post-freeze packages that were in each capture's panel)
and UPPER (every post-freeze package at every partition; a sensitivity scenario,
not a bound over intermediate cases). Standard library only; writes one JSON.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
import data_sanity_gate as G
import evaluate_axis3_v2h1 as E
import t2_deps_v2h1_collect as collect

Q = REPO / "data" / "quarantine" / "axis3-deps-v2"
EVIDENCE = Q / "verdict-2026-09-14"
FREEZE_REV = "aaeefa43"      # first v2h.1 capture commit: the panel as frozen by the record
VERDICT_REV = "13742753"     # HEAD when the verdict was adjudicated (pins/id_map at that time)
CALIBRATION = Q / "sanity-calibration-3e51319d9817.json"
DRIFT_PARTITIONS = ["2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31"]
HASH_CHECK_FROM = "2026-08-03"   # last pre-drift capture: a control the method must also match
CUTOFFS = [  # forward cutoffs of the v2h.2 record: (as_of, committed gate check, committed evaluation)
    ("2026-08-17", "sanity-check-98bab4ff31d3.json", "v2h1-live-2026-08-17-2da01f9e926f.json"),
    ("2026-08-24", "sanity-check-9ec385dfa6be.json", "v2h1-live-2026-08-24-4cd020c1add4.json"),
    ("2026-08-31", "sanity-check-3ce743562e36.json", "v2h1-live-2026-08-31-e34f80ae4f53.json"),
]
LATEST_GATE = "sanity-check-3ce743562e36.json"


def _show(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{path}"],
                          capture_output=True, check=True).stdout


def panel_at(rev: str) -> dict:
    """entity_id -> {"SYS/name"}, mirroring t2_deps_v2h1_collect.load_panel() at `rev`.
    Strings match the collector's self_names spelling, so exclusion is exact."""
    manifest = json.loads(_show(rev, "data/quarantine/axis3-deps-v2/expansion-manifest-DRAFT.json"))
    pins = json.loads(_show(rev, "data/deps_id_map.json"))["pins"]
    id_map = json.loads(_show(rev, "etl/id_map.json"))
    ent = defaultdict(set)
    for info in manifest["repos"].values():
        for p in info.get("declared_packages", []):
            if p.get("depsdev_exists"):
                ent[info.get("entity_id")].add(f"{p['system'].upper()}/{p['package']}")
    for repo, pin in pins.items():
        if repo in id_map:
            ent[id_map[repo]].add(f"{pin['system'].upper()}/{pin['package']}")
    return ent


def main() -> int:
    frozen = panel_at(FREEZE_REV)
    later = panel_at(VERDICT_REV)
    owner = {pkg: eid for eid, pkgs in frozen.items() for pkg in pkgs}
    changed = sorted(e for e in frozen if later.get(e, set()) != frozen[e])

    # Capture membership: a post-freeze system was in a capture's panel iff it produced rows.
    rows_at = defaultdict(set)
    for f in (REPO / "data" / "observations").glob("*/deps_v2h1-????-??-??.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                if row["entity_id"] not in frozen:
                    rows_at[(row.get("snapshot_at") or "")[:10]].add(row["entity_id"])
    # Proof of that reconstruction, stronger than an entity count: rebuild each capture's
    # SQL (CASE map + self_names) and match the query hash its manifest recorded.
    query_hash_check = {}
    for mf in (REPO / "data" / "observations").glob("*/deps_v2h1-*-manifest.json"):
        m = json.loads(mf.read_text())
        p = m.get("partition_day") or ""
        if p < HASH_CHECK_FROM:
            continue
        members = {e: frozen[e] for e in frozen} | {e: later[e] for e in rows_at[p]}
        panel = {e: {tuple(s.split("/", 1)) for s in pkgs} for e, pkgs in members.items()}
        sql_sha = hashlib.sha256(collect.build_query(panel, p).encode()).hexdigest()
        query_hash_check[p] = sql_sha == m.get("query_sha256")
    query_hash_ok = set(DRIFT_PARTITIONS) <= set(query_hash_check) and all(query_hash_check.values())
    in_panel = {p: {pkg for e in rows_at[p] for pkg in later[e]} for p in DRIFT_PARTITIONS}
    all_new = {pkg for e, pkgs in later.items() if e not in frozen for pkg in pkgs}

    sql_text = (EVIDENCE / "bq-query.sql").read_text()
    pulled_names = set(re.findall(r'"([^"]+)"', sql_text.split("d.Dependent.Name IN", 1)[1]))
    uncovered = sorted(pkg for pkg in all_new
                       if pkg.split("/", 1)[0] not in ("PYPI", "NPM") or pkg.split("/", 1)[1] not in pulled_names)
    names_ok = not uncovered

    pulled = json.loads((EVIDENCE / "bq-excluded-dependents.json").read_text())
    pairs = [r for r in pulled if f"{r['sys']}/{r['name']}" in owner]

    def correction(member) -> dict:
        corr = defaultdict(set)
        for r in pairs:
            dep = f"{r['dep_sys']}/{r['dep_name']}"
            if dep in member(r["snap"]):
                corr[(owner[f"{r['sys']}/{r['name']}"], r["snap"])].add(dep)  # dedup per system
        return corr

    variants = {"FILTER_ONLY": {}, "EXACT": correction(lambda p: in_panel[p]),
                "UPPER": correction(lambda p: all_new)}
    gate_loader, eval_loader = G.deps_v2h1_series, E.load_series
    committed_gate = json.loads((Q / LATEST_GATE).read_text())["verdicts"]
    results = {}
    for name, corr in variants.items():
        def restore(series, corr=corr):
            out = {}
            for eid, pts in series.items():
                if eid not in frozen:
                    continue
                if isinstance(pts, dict):
                    out[eid] = {s: v + len(corr.get((eid, s), ())) for s, v in pts.items()}
                else:
                    out[eid] = [(s, v + len(corr.get((eid, s), ()))) for s, v in pts]
            return out

        def gate_series(restore=restore):
            series, _ = gate_loader()
            fixed, cov = restore(series), defaultdict(int)
            for pts in fixed.values():
                for s in pts:
                    cov[s] += 1
            return fixed, cov

        with tempfile.TemporaryDirectory() as tmp:
            G.deps_v2h1_series, G.OUT = gate_series, Path(tmp)
            # check() prints its artifact path relative to the repo; the replay writes to a
            # temp dir on purpose (no stray gate artifacts), so that print is swallowed.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.suppress(ValueError):
                G.check(str(CALIBRATION), "v2h1")
            replay_gate = json.loads(next(Path(tmp).glob("sanity-check-*.json")).read_text())
        gate_diffs = sorted(s for s in committed_gate
                            if committed_gate[s]["status"] != replay_gate["verdicts"][s]["status"])

        E.load_series = lambda as_of, restore=restore: restore(eval_loader(as_of))
        cutoffs = {}
        for as_of, gate, art in CUTOFFS:
            r = E.evaluate(as_of, "live", Q / gate)
            c = json.loads((Q / "eval" / art).read_text())
            rc, cc = r["criteria"], c["criteria"]
            same_votes = set(r["per_entity"]) == set(c["per_entity"]) and all(
                r["per_entity"][k]["rising"] == c["per_entity"][k]["rising"]
                and r["per_entity"][k]["unstable"] == c["per_entity"][k]["unstable"]
                for k in c["per_entity"])
            cutoffs[as_of] = {
                "criteria_pass_identical": {k: v["pass"] for k, v in rc.items()} ==
                                           {k: v["pass"] for k, v in cc.items()},
                "rising_identical": r["rising"] == c["rising"],
                "votes_and_unstable_identical": same_votes,
                "canary_identical": r["canary"] == c["canary"],
                "c3_flips_identical": [t.get("flip") for t in rc["c3_flip"]["transitions"]] ==
                                      [t.get("flip") for t in cc["c3_flip"]["transitions"]],
                "c2_committed_replay": [cc["c2_independence"]["value"], rc["c2_independence"]["value"]],
                "c4_panel_share_committed_replay": [cc["c4_nondegeneracy"]["panel_share"],
                                                    rc["c4_nondegeneracy"]["panel_share"]],
                "max_abs_z_shift": round(max(abs(r["per_entity"][k]["z"] - c["per_entity"][k]["z"])
                                             for k in c["per_entity"]), 4),
            }
        G.deps_v2h1_series, E.load_series = gate_loader, eval_loader
        results[name] = {
            "correction": {f"{e}@{s}": sorted(d) for (e, s), d in sorted(corr.items())},
            "gate_status_diffs": gate_diffs,
            "gate_flagged": replay_gate["flagged"],
            "cutoffs": cutoffs,
        }

    invariant = query_hash_ok and names_ok and not changed and all(
        not v["gate_status_diffs"] and all(
            x["criteria_pass_identical"] and x["rising_identical"] and x["votes_and_unstable_identical"]
            and x["canary_identical"] and x["c3_flips_identical"] for x in v["cutoffs"].values())
        for v in results.values())
    out = {
        "v": "axis3_v2h1_frozen_panel_replay_2",
        "record": "governance/AXIS3-DEPS-V2H2-VERDICT-2026-09-14.md",
        "freeze_rev": FREEZE_REV, "verdict_rev": VERDICT_REV,
        "frozen_panel": {"systems": len(frozen), "package_strings": len(owner),
                         "frozen_systems_with_changed_package_sets": changed},
        "capture_query_hash_check": dict(sorted(query_hash_check.items())),
        "capture_query_hash_ok": query_hash_ok,
        "post_freeze_packages_in_capture_panel": {p: sorted(v) for p, v in in_panel.items()},
        "pull_uncovered_post_freeze_packages": uncovered,
        "bigquery_pull": json.loads((EVIDENCE / "bq-job.json").read_text()),
        "excluded_pairs_touching_frozen_packages": sorted(
            {(r["snap"], f"{r['sys']}/{r['name']}", f"{r['dep_sys']}/{r['dep_name']}") for r in pairs}),
        "variants": results,
        "verdict_invariant": invariant,
    }
    (EVIDENCE / "replay-results.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"frozen panel {len(frozen)} systems; query hashes {query_hash_check}; "
          f"pull covers all post-freeze names: {names_ok}; "
          f"excluded pairs touching frozen packages: {len(out['excluded_pairs_touching_frozen_packages'])}")
    for name, v in results.items():
        print(f"  {name}: correction {v['correction']} | gate diffs {v['gate_status_diffs']} | "
              + " | ".join(f"{k}: votes {x['votes_and_unstable_identical']}, max dz {x['max_abs_z_shift']}"
                           for k, x in v["cutoffs"].items()))
    print(f"VERDICT INVARIANT: {invariant}")
    return 0 if invariant else 1


if __name__ == "__main__":
    raise SystemExit(main())
