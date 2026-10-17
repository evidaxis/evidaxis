#!/usr/bin/env python3
"""Write aggregate rehearsal evidence without publishing candidate data."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.gh_graphql import departure_cap


def build_report(candidate: dict, previous: dict, departures: list, seed_count: int, jobs: list) -> dict:
    current_ids = {entity["entity_id"] for entity in candidate["entities"]}
    previous_ids = {entity["entity_id"] for entity in previous["entities"]}
    durations = []
    for job in jobs:
        for step in job.get("steps", []):
            start, end = step.get("started_at"), step.get("completed_at")
            if start and end:
                durations.append({"step": step["name"], "conclusion": step.get("conclusion"),
                                  "seconds": (datetime.fromisoformat(end.replace("Z", "+00:00"))
                                              - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds()})
    cap = departure_cap(seed_count)
    return {
        "release_date": candidate["snapshot_date"], "previous_date": previous["snapshot_date"],
        "methodology_version": candidate["methodology_version"],
        "systems": len(current_ids), "previous_systems": len(previous_ids),
        "delta": len(current_ids) - len(previous_ids), "missing_since_previous": len(previous_ids - current_ids),
        "departures": len(departures), "departure_cap": cap, "within_cap": len(departures) <= cap,
        "steps": durations,
    }


def summary(report: dict) -> str:
    return (f"Rehearsal {report['release_date']}: {report['methodology_version']}; "
            f"systems {report['systems']} vs {report['previous_systems']} ({report['delta']:+d}); "
            f"missing {report['missing_since_previous']}; departures {report['departures']}/{report['departure_cap']}; "
            f"cap {'PASS' if report['within_cap'] else 'FAIL'}; step durations in rehearsal-report.json.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--summary-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.summary_dir
    output.mkdir(parents=True, exist_ok=True)
    try:
        snapshots = args.data_dir / "snapshots"
        candidate = json.loads((snapshots / args.date / "snapshot.json").read_text())
        if candidate["snapshot_date"] != args.date:
            raise ValueError("candidate date differs from release_date")
        prior_date = max(p.name for p in snapshots.iterdir() if p.is_dir() and p.name < args.date)
        previous = json.loads((snapshots / prior_date / "snapshot.json").read_text())
        preflight = json.loads((output / "summary-graphql.json").read_text())
        jobs = json.loads((output / "jobs.json").read_text())["jobs"]
        report = build_report(candidate, previous, preflight["departed"], preflight["repos"], jobs)
        line = summary(report)
        code = 0 if report["within_cap"] else 1
    except (OSError, ValueError, KeyError) as exc:
        # A failed capture must leave an honest artifact, never a reassuring empty report.
        report = {"release_date": args.date, "error": type(exc).__name__, "complete": False}
        line = f"Rehearsal {args.date}: incomplete; inspect the failed step."
        code = 1
    (output / "rehearsal-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(line)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(line + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
