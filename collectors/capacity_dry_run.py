#!/usr/bin/env python3
"""capacity_dry_run - measure what servicing the whole pending registry costs.

The 2026-09-20 growth-policy amendment replaced a calendar publication rate with a
measured limit, and requires this run before the first tranche under it: the size of
a tranche has to follow from what the registry can actually service, measured at the
intended size rather than extrapolated from a sample.

It performs the same two GitHub REST calls the daily collector performs per card, over
every pending member, and reports request count, retries, failures, wall time, observed
throughput and the remaining rate-limit budget. It writes nothing but its own report:
no seeds are activated and no card is published by this tool.

Usage: python collectors/capacity_dry_run.py [--limit N] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST_GLOB = "data/census/*/pending-manifest.json"
DEFAULT_OUT = ROOT / "data/census/capacity-dry-run.json"


def gh(path: str) -> tuple[bool, int]:
    """One API call; returns success and the number of attempts spent."""
    for attempt in range(1, 4):
        result = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if result.returncode == 0:
            return True, attempt
        if "rate limit" in (result.stderr or "").lower():
            time.sleep(60)
            continue
        return False, attempt
    return False, 3


def rate_limit() -> dict:
    result = subprocess.run(["gh", "api", "rate_limit"], capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    return json.loads(result.stdout)["resources"]["core"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    manifests = sorted(ROOT.glob(MANIFEST_GLOB))
    if not manifests:
        print("no pending manifest found")
        return 2
    members = [m for m in json.loads(manifests[-1].read_text())["members"]
               if m.get("status") == "pending"]
    if args.limit:
        members = members[: args.limit]

    started = time.monotonic()
    before = rate_limit()
    calls = retries = failures = 0
    for index, member in enumerate(members, start=1):
        repo = member["full_name"]
        for path in (f"repos/{repo}", f"repos/{repo}/stats/commit_activity"):
            ok, attempts = gh(path)
            calls += 1
            retries += attempts - 1
            failures += 0 if ok else 1
        if index % 250 == 0:
            rate = index / (time.monotonic() - started)
            print(f"  {index}/{len(members)} · {rate:.1f} repos/s · {failures} failures", flush=True)
    elapsed = time.monotonic() - started
    after = rate_limit()

    report = {
        "@type": "CapacityDryRun",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "members_measured": len(members),
        "calls": calls,
        "retries": retries,
        "failures": failures,
        "wall_seconds": round(elapsed, 1),
        "seconds_per_member": round(elapsed / max(len(members), 1), 3),
        "rate_limit_before": before.get("remaining"),
        "rate_limit_after": after.get("remaining"),
        "rate_limit_ceiling_per_hour": after.get("limit"),
        "money_cost_usd": 0,
        "note": (
            "Same two REST calls per card as the daily collector. Writes no seeds and "
            "publishes nothing; required by GROWTH-POLICY-AMENDMENT-2026-09-20.md before "
            "the first capacity-bounded tranche."
        ),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
