#!/usr/bin/env python3
"""activation_tranche - the weekly card-activation tranche (mechanical, no taste).

Policy (REGISTRY-GROWTH-POLICY-2026-07-21.md, founder decisions of the same day):
  size  n_t = min(P_t, max(10, ceil(0.06 * L_t)))
        L_t = live cards read at a UTC cutoff taken BEFORE the run
        P_t = pending queue length at that same cutoff
  order FORWARD crossings first, then BACKLOG; within each queue current
        GitHub stars DESC, tie-break repository ID ASC
  claim "publication order is a marketing schedule, never a measurement
         verdict; membership is complete and auditable from the manifest"

The two queues implement the policy's "forward crossings take priority from
2026-08-01 so new coverage debt never accumulates". Sorting one merged queue by
stars would bury a fresh 501-star crossing behind the entire backlog and quietly
invert that priority (red-team finding #15, 2026-08-03). Queue membership is
mechanical: the census that admitted a member stamps wave=backlog for the first
stock census and wave=forward for every later one.

Inputs : data/census/<month>/pending-manifest.json (membership, positive-only)
         etl/seeds.json                            (live cards = current members)
Outputs: data/census/<month>/tranches/<date>-tranche.json  (what to activate)
         --apply also appends the tranche members into etl/seeds.json under
         cohort "unassigned-v1" and prints the frontier-manifest command that
         CI requires to pair with any seeds.json change.

Stars are RE-READ LIVE at tranche time (the policy says "current stars"), so the
order reflects the week of publication, not the census month. A member whose
repo went missing/archived since the census is skipped and reported (it stays in
the pending manifest: membership is never silently revoked).

Usage:
  python3 collectors/activation_tranche.py --month 2026-08            # dry-run
  python3 collectors/activation_tranche.py --month 2026-08 --apply
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEEDS = REPO / "etl" / "seeds.json"


def gh_repo(full_name: str) -> dict | None:
    p = subprocess.run(
        ["gh", "api", f"repos/{full_name}",
         "--jq", "{id:.id, full_name:.full_name, stars:.stargazers_count, "
                 "archived:.archived, fork:.fork}"],
        capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return None


def live_card_count() -> int:
    seeds = json.loads(SEEDS.read_text())
    return sum(len(v["entities"]) for v in seeds["verticals"].values())


def main() -> int:
    args = sys.argv[1:]
    month = (args[args.index("--month") + 1] if "--month" in args
             else datetime.now(timezone.utc).strftime("%Y-%m"))
    apply = "--apply" in args
    month_dir = REPO / "data" / "census" / month
    mp = month_dir / "pending-manifest.json"
    if not mp.exists():
        print(f"no pending manifest: {mp}")
        return 2
    manifest = json.loads(mp.read_text())
    pending = [m for m in manifest["members"] if m.get("status") == "pending"]
    live = live_card_count()
    size = min(max(10, math.ceil(0.06 * live)), len(pending))
    print(f"live cards={live} · pending={len(pending)} · "
          f"tranche size={size} (max(10, ceil(0.06*{live})))")
    if not pending:
        print("pending queue empty - nothing to activate")
        return 0

    # Re-read live stars for the whole pending queue (order is "current stars").
    print("re-reading live stars for the pending queue ...")
    refreshed, missing = [], []
    for i, m in enumerate(pending, 1):
        info = gh_repo(m["full_name"])
        if info is None or info.get("archived") or info.get("fork"):
            missing.append(m["full_name"])
        else:
            refreshed.append({**m, "stars": info["stars"],
                              "repo_id": info["id"],
                              "full_name": info["full_name"]})
        if i % 50 == 0:
            print(f"  {i}/{len(pending)}", flush=True)
        time.sleep(0.35)

    refreshed.sort(key=lambda m: (-m["stars"], m["repo_id"]))
    tranche = refreshed[:size]
    today = datetime.now(timezone.utc).date().isoformat()
    out_dir = month_dir / "tranches"
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "@type": "ActivationTranche",
        "date": today,
        "formula": "max(10, ceil(0.06 * live_cards)), capped by pending queue",
        "live_cards_before": live,
        "pending_before": len(pending),
        "order": "current stars desc, tie repository id asc",
        "disclaimer": ("Order of publication is a marketing schedule, never a "
                       "measurement verdict. Membership is complete from the "
                       "pending manifest; cards index after 4 weekly "
                       "observations."),
        "skipped_unavailable": missing,
        "members": tranche,
    }
    out = out_dir / f"{today}-tranche.json"
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    for m in tranche:
        print(f"  {m['stars']:>7}★  {m['full_name']}")
    if missing:
        print(f"skipped (archived/fork/gone since census): {len(missing)}")
    print(f"written: {out}")

    if not apply:
        print("\ndry-run. re-run with --apply to write seeds.json")
        return 0

    seeds = json.loads(SEEDS.read_text())
    vert = seeds["verticals"].setdefault("unassigned-v1", {
        "label": "Unassigned (AI-v1 census)",
        "industry_slug": "ai", "subniche_slug": "unassigned",
        "entities": []})
    have = {e["github_repo"].lower()
            for v in seeds["verticals"].values() for e in v["entities"]}
    added = 0
    for m in tranche:
        if m["full_name"].lower() in have:
            continue
        vert["entities"].append({
            "github_repo": m["full_name"], "entity_type": "repo",
            "name": m["full_name"].split("/")[-1],
            "homepage": f"https://github.com/{m['full_name']}",
            "openalex_work_ids": [],
            "note": f"Admitted by AI-v1 census {month}; axis-2 unresolved.",
        })
        added += 1
    seeds["meta"][f"census_{month}"] = (
        f"{today}: activation tranche of {added} members "
        f"(policy: max(10, 6% of live cards), stars desc)")
    SEEDS.write_text(json.dumps(seeds, ensure_ascii=False, indent=1))

    # CI requires a dated frontier manifest paired with any seeds.json change.
    scan = {
        "method": ("AI-v1 monthly census -> weekly activation tranche "
                   "(mechanical: max(10, 6% live), current stars desc)"),
        "sources": ["github-search-api", "github-graphql"],
        "examined_estimate": rec["pending_before"],
        "candidates": [{"repo": m["full_name"], "cohort": "unassigned-v1",
                        "stars": m["stars"], "axes_observed": "github",
                        "note": "activated from pending manifest"}
                       for m in tranche],
    }
    scan_p = out_dir / f"{today}-frontier-input.json"
    scan_p.write_text(json.dumps(scan, ensure_ascii=False, indent=1))
    print(f"\nseeds.json: +{added} entities")
    print(f"NEXT (CI pairing): python3 collectors/frontier_manifest.py "
          f"--input {scan_p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
