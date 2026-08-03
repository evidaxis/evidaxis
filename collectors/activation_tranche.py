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
repo went missing/archived since the census is skipped and reported with the
terminal status ``unavailable``: membership is never silently revoked, but an
unavailable member cannot occupy the pending queue forever.

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


def gh_repos_batch(names: list[str]) -> dict[str, dict]:
    """Live stars for the whole pending queue, batched.

    One REST call per member re-read 7,410 members at ~0.35s each: 43 minutes
    to choose ten cards. The queue must be read whole (the policy orders by
    CURRENT stars, not census stars), so the fix is batching, not sampling -
    sampling would let a member that gained stars since the census sort below
    one that lost them, which is precisely the ordering the policy fixes.
    """
    out: dict[str, dict] = {}
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        parts = []
        for j, fn in enumerate(batch):
            if "/" not in fn:
                continue
            owner, name = fn.split("/", 1)
            parts.append(
                f'r{j}: repository(owner:"{owner}", name:"{name}") {{'
                f' databaseId nameWithOwner stargazerCount isArchived isFork }}')
        if not parts:
            continue
        p = subprocess.run(
            ["gh", "api", "graphql", "-f",
             "query=query {" + " ".join(parts) + "}"],
            capture_output=True, text=True, timeout=180)
        try:
            data = (json.loads(p.stdout).get("data") or {}) if p.stdout else {}
        except json.JSONDecodeError:
            data = {}
        for j, fn in enumerate(batch):
            node = data.get(f"r{j}")
            if node:
                out[fn] = {"id": node["databaseId"],
                           "full_name": node["nameWithOwner"],
                           "stars": node["stargazerCount"],
                           "archived": node["isArchived"],
                           "fork": node["isFork"]}
        if (i // 50) % 20 == 0:
            print(f"  live stars {i}/{len(names)}", flush=True)
        time.sleep(0.2)
    return out


def live_card_count() -> int:
    seeds = json.loads(SEEDS.read_text())
    return sum(len(v["entities"]) for v in seeds["verticals"].values())


def seeded_repo_ids(seeds: dict) -> set[int]:
    """Resolve live-card identity without trusting a repository's mutable name.

    Legacy cards predate an inline ``repo_id``, so their numeric identities come
    from registry_ids.json. Census-activated cards retain the id either inline
    or in a published pending manifest. Names are used only to locate those
    identity records; the returned ids are the sole membership dedup keys.
    """
    entities = [
        entity
        for vertical in seeds["verticals"].values()
        for entity in vertical["entities"]
    ]
    seed_names = {entity["github_repo"].lower() for entity in entities}
    repo_ids = {
        entity["repo_id"]
        for entity in entities
        if isinstance(entity.get("repo_id"), int)
    }

    registry_path = REPO / "data" / "registry_ids.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text()).get("members", {})
        for recorded_name, identity in registry.items():
            aliases = {recorded_name.lower()}
            if identity.get("canonical"):
                aliases.add(identity["canonical"].lower())
            if aliases & seed_names:
                repo_ids.add(identity["repo_id"])

    for manifest_path in (REPO / "data" / "census").glob(
            "*/pending-manifest.json"):
        historic = json.loads(manifest_path.read_text())
        for member in historic.get("members", []):
            if member.get("full_name", "").lower() in seed_names:
                repo_ids.add(member["repo_id"])
    return repo_ids


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
    live_info = gh_repos_batch([m["full_name"] for m in pending])
    refreshed, missing = [], []
    unavailable_ids = set()
    for m in pending:
        info = live_info.get(m["full_name"])
        if info is None or info["archived"] or info["fork"]:
            missing.append(m["full_name"])
            unavailable_ids.add(m["repo_id"])
        else:
            refreshed.append({**m, "stars": info["stars"],
                              "repo_id": info["id"],
                              "full_name": info["full_name"]})

    # TWO queues, not one sorted list. The module header claimed this from the
    # start while the code sorted a single merged queue by stars - a docstring
    # that lies is worse than no docstring, because review reads it as done.
    # Merged, a fresh 501-star forward crossing waits behind thousands of
    # backlog members and the policy's "forward crossings take priority so new
    # coverage debt never accumulates" is inverted in production, forever,
    # since the same code re-runs every week.
    def key(m):
        return (-m["stars"], m["repo_id"])

    forward = sorted([m for m in refreshed if m.get("wave") == "forward"], key=key)
    backlog = sorted([m for m in refreshed if m.get("wave") != "forward"], key=key)
    tranche = (forward + backlog)[:size]
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
    have = seeded_repo_ids(seeds)
    added = 0
    for m in tranche:
        if m["repo_id"] in have:
            continue
        vert["entities"].append({
            "github_repo": m["full_name"], "entity_type": "repo",
            "repo_id": m["repo_id"],
            "name": m["full_name"].split("/")[-1],
            "homepage": f"https://github.com/{m['full_name']}",
            "openalex_work_ids": [],
            "note": f"Admitted by AI-v1 census {month}; axis-2 unresolved.",
        })
        have.add(m["repo_id"])
        added += 1
    seeds["meta"][f"census_{month}"] = (
        f"{today}: activation tranche of {added} members "
        f"(policy: max(10, 6% of live cards), forward queue then backlog)")
    SEEDS.write_text(json.dumps(seeds, ensure_ascii=False, indent=1))

    # Close the loop on the pending queue. Without this the status stays
    # "pending" forever: next week P_t is unchanged, the same high-star heads
    # are re-selected, apply skips them as already present, added=0, and the
    # backlog never drains while the tranche artifact claims a full activation.
    # The manifest is therefore a LIVING queue; the immutable admission record
    # is census-run.json plus this file's original hash, both already written.
    activated = {m["repo_id"] for m in tranche}
    for member in manifest["members"]:
        if member["repo_id"] in activated:
            member["status"] = "activated"
            member["activated_on"] = today
        elif member["repo_id"] in unavailable_ids:
            member["status"] = "unavailable"
            member["unavailable_on"] = today
    manifest["queue_note"] = (
        "status transitions pending -> activated as weekly tranches publish, "
        "or pending -> unavailable when a repository is gone, archived, or a "
        "fork; "
        "the frozen admission record is census-run.json and the manifest hash "
        "recorded there at census time")
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"pending manifest: {len(activated)} marked activated, "
          f"{len(unavailable_ids)} marked unavailable, "
          f"{sum(1 for m in manifest['members'] if m['status'] == 'pending')} "
          f"still pending")

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
