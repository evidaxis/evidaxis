#!/usr/bin/env python3
"""Replay one collected rehearsal candidate and, when asked, inject one fault.

The fault exists only in the directory this process is given. Nothing is committed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

DRILLS = ("none", "site_test", "hf_handle", "canary_missing")
# Projection drops github_repo when that same key is User, so a User row alone stays green.
# The guard treats a login as personal when any owner_types row is User.
LEAKED_REPO = "drill-person-handle/repo"
USER_ROW = "drill-person-handle/home"
# classification_for rejects a row without a positive int repo_id; this id is not fetched.
FICTIONAL_REPO_ID = 900_000_001
DRILL_TEST = Path("web/src/lib/__drill__.test.ts")
DRILL_TEST_BODY = "import { expect, it } from 'vitest';\n\nit('rehearsal drill', () => {\n  expect(1).toBe(2);\n});\n"
CHECK_STEPS = (
    ("hf", "Check the HF publication projection"),
    ("verify", "Verify the site against this rehearsal candidate"),
    ("report", "Rehearsal report"),
)
# The step that must catch each drill. Another failure is not a catch.
EXPECTED = {"site_test": "verify", "canary_missing": "verify", "hf_handle": "hf"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ARTIFACT_DATE = re.compile(r"^snapshot-(\d{4}-\d{2}-\d{2})-\d+$")
_SUMMARY_FILE = re.compile(r"^(jobs|timing|rehearsal-report|summary-.+)\.json$")


def current_methodology(root: Path) -> str:
    registry = json.loads((root / "web/src/lib/methodology-registry.json").read_text(encoding="utf-8"))
    current = [row["version"] for row in registry.get("versions", []) if row.get("status") == "current"]
    if len(current) != 1:
        raise ValueError("methodology registry must name one current version")
    return current[0]


def apply_drill(root: Path, drill: str, date: str | None = None) -> None:
    if drill not in DRILLS:
        raise SystemExit(f"unknown drill {drill}")
    if drill == "none":
        return
    if drill == "site_test":
        path = root / DRILL_TEST
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DRILL_TEST_BODY, encoding="utf-8")
        return
    if drill == "canary_missing":
        version = current_methodology(root)
        path = root / "web/src/data/methodology-control-baselines" / f"{version}.json"
        if not path.is_file():
            raise SystemExit(f"missing control baseline {path}")
        path.unlink()
        return
    if not date:
        raise SystemExit("hf_handle needs --date")
    owners_path = root / "etl" / "owner_types.json"
    owners = json.loads(owners_path.read_text(encoding="utf-8"))
    repos = owners["repos"]
    repos[LEAKED_REPO] = {
        "owner_type": "Organization",
        "repo_id": FICTIONAL_REPO_ID,
        "full_name": LEAKED_REPO,
    }
    repos[USER_ROW] = {
        "owner_type": "User",
        "repo_id": FICTIONAL_REPO_ID + 1,
        "full_name": USER_ROW,
    }
    owners_path.write_text(json.dumps(owners, indent=2) + "\n", encoding="utf-8")
    snap_path = root / "data" / "snapshots" / date / "snapshot.json"
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    target = next((entity for entity in snap.get("entities", []) if isinstance(entity, dict) and entity.get("github_repo")), None)
    if target is None:
        raise SystemExit("candidate has no github_repo")
    target["github_repo"] = LEAKED_REPO
    snap_path.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")


def _artifact_date(snapshot_json: Path, download_dir: Path) -> str | None:
    for part in snapshot_json.relative_to(download_dir).parts:
        match = _ARTIFACT_DATE.match(part)
        if match:
            return match.group(1)
    return None


def _choose_snapshot(found: list[Path]) -> Path:
    if len(found) == 1:
        return found[0]
    dated = [path for path in found if _DATE.match(path.parent.name)]
    if len(dated) == 1:
        return dated[0]
    raise SystemExit("artifact contains more than one snapshot.json")


def place_replay(download_dir: Path, data_dir: Path, summary_dir: Path | None = None) -> str:
    found = [path for path in download_dir.rglob("snapshot.json") if path.is_file()]
    if not found:
        raise SystemExit("artifact has no snapshot.json")
    chosen = _choose_snapshot(found)
    payload = json.loads(chosen.read_text(encoding="utf-8"))
    date = payload.get("snapshot_date")
    if not isinstance(date, str) or not _DATE.match(date):
        raise SystemExit("snapshot.json has no snapshot_date")
    named = _artifact_date(chosen, download_dir)
    if named and named != date:
        raise SystemExit(f"artifact name date {named} != snapshot_date {date}")
    dest = data_dir / "snapshots" / date
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for item in chosen.parent.iterdir():
        if item.is_file() and not _SUMMARY_FILE.match(item.name):
            shutil.copy2(item, dest / item.name)
    if summary_dir is not None:
        summary = next((path for path in download_dir.rglob("summary-graphql.json") if path.is_file()), None)
        if summary is not None:
            summary_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(summary, summary_dir / "summary-graphql.json")
    # The site reads data/latest.json to pick its current snapshot; point it at the
    # candidate, keeping the pointer's own fields, as the collector would.
    latest = data_dir / "latest.json"
    pointer = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else {}
    keys = list(pointer) or ["snapshot_date", "period", "snapshot_id", "methodology_version"]
    latest.write_text(json.dumps({key: payload.get(key) for key in keys if key in payload or key == "snapshot_date"},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    env_path = os.environ.get("GITHUB_ENV")
    if env_path:
        with open(env_path, "a", encoding="utf-8") as stream:
            stream.write(f"SNAPSHOT_DATE={date}\n")
    print(date)
    return date


def drill_verdict(drill: str, outcomes: dict) -> tuple[str, int]:
    if drill not in DRILLS:
        raise SystemExit(f"unknown drill {drill}")
    failed = [name for key, name in CHECK_STEPS if outcomes.get(key) == "failure"]
    if drill == "none":
        if failed:
            return f"drill none: failed at step {failed[0]}", 1
        if any(outcomes.get(key) != "success" for key, _name in CHECK_STEPS):
            return "drill none: checks did not run", 1
        return "drill none: checks passed", 0
    names = dict(CHECK_STEPS)
    expected = EXPECTED[drill]
    if outcomes.get(expected) != "failure":
        return f"drill {drill}: NOT caught", 1
    # The report reads the failed step, so its failure follows the catch.
    other = [names[key] for key, _name in CHECK_STEPS
             if key not in (expected, "report") and outcomes.get(key) == "failure"]
    if other:
        return f"drill {drill}: caught at step {names[expected]}, but also failed at step {other[0]}", 1
    return f"drill {drill}: caught at step {names[expected]}", 0


def _write_summary(line: str) -> None:
    print(line)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="cmd", required=True)

    place = commands.add_parser("place")
    place.add_argument("--download", type=Path, required=True)
    place.add_argument("--data-dir", type=Path, default=Path("data"))
    place.add_argument("--summary-dir", type=Path, default=None)

    apply = commands.add_parser("apply")
    apply.add_argument("--drill", required=True)
    apply.add_argument("--date", default=os.environ.get("SNAPSHOT_DATE"))
    apply.add_argument("--root", type=Path, default=Path("."))

    commands.add_parser("verdict")
    args = parser.parse_args(argv)
    if args.cmd == "place":
        place_replay(args.download, args.data_dir, args.summary_dir)
        return 0
    if args.cmd == "apply":
        apply_drill(args.root, args.drill, args.date)
        return 0
    outcomes = {key: os.environ.get(key.upper(), "skipped") for key, _name in CHECK_STEPS}
    line, code = drill_verdict(os.environ.get("DRILL", ""), outcomes)
    _write_summary(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
