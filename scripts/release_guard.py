#!/usr/bin/env python3
"""Resolve the weekly label and admit a release before any collection or writes."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def release_date(value: str, mode: str, now: datetime | None = None) -> str:
    if mode not in ("release", "rehearsal"):
        raise ValueError("mode must be release or rehearsal")
    today = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    if not value:
        day = today - timedelta(days=(today.weekday() - 5) % 7)
    else:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("release_date must be YYYY-MM-DD")
        day = datetime.strptime(value, "%Y-%m-%d").date()
    if day.weekday() != 5:
        raise ValueError("release_date must be a Saturday")
    if mode == "release" and day > today:
        raise ValueError("release_date cannot be in the future for release")
    return day.isoformat()


def already_exists(data: Path, day: str, mode: str, runs: list[dict], current_id: str = "") -> bool:
    if mode != "release":
        return False
    return (data / "snapshots" / day).exists() or any(
        run.get("display_title") == f"weekly release {day}"
        and run.get("head_branch") == "main"
        and run.get("conclusion") == "success"
        and str(run.get("id")) != current_id
        for run in runs
    )


def github_request(path: str, payload: dict | None = None):
    request = Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )
    # Bound API waits so an unknown state fails before collection, never admits it.
    with urlopen(request, timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else None


def successful_runs() -> list[dict]:
    runs = []
    page = 1
    while True:
        query = urlencode({"branch": "main", "status": "success", "per_page": 100, "page": page})
        batch = github_request(f"actions/workflows/weekly-snapshot.yml/runs?{query}")
        runs.extend(batch["workflow_runs"])
        if len(runs) >= batch["total_count"]:
            return runs
        if not batch["workflow_runs"] or len(runs) >= 1000:
            raise ValueError("GitHub run history incomplete; refusing collection")
        page += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", action="store_true")
    args = parser.parse_args()
    mode = os.environ.get("MODE", "release")
    day = release_date(os.environ.get("INPUT_DATE", ""), mode)
    data = Path("data")
    skip = already_exists(data, day, mode, [])
    if mode == "release" and not skip:
        skip = already_exists(data, day, mode, successful_runs(), os.environ.get("GITHUB_RUN_ID", ""))
    if skip:
        # Sensors read the skipped snapshot job/collection step via Jobs API;
        # this green no-op must never stand in for a successful publication.
        print(f"already exists (уже есть): {day}; no collection or commit")
    elif mode == "release" and os.environ["GITHUB_REF_NAME"] != "main":
        raise ValueError("new releases must run on main; use rehearsal on a test branch")
    elif args.route:
        # run-name cannot evaluate dates. Only this dated child may collect or deploy.
        github_request("actions/workflows/weekly-snapshot.yml/dispatches", {
            "ref": os.environ["GITHUB_REF_NAME"], "inputs": {"mode": mode, "release_date": day},
        })
        print(f"requested weekly {mode} {day}; this routing run does not collect")
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"date={day}\nmode={mode}\nskip={str(skip).lower()}\n")


if __name__ == "__main__":
    main()
