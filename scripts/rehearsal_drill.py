#!/usr/bin/env python3
"""Replay one collected rehearsal candidate and, when asked, inject one fault.

The fault exists only in the directory this process is given. Nothing is committed.
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
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
# The leaked handle also trips the site's person-free guard: a second catch, not a fault.
ALSO_CATCHES = {"hf_handle": {"verify"}}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ARTIFACT_DATE = re.compile(r"^snapshot-(\d{4}-\d{2}-\d{2})-\d+$")
_SUMMARY_FILE = re.compile(r"^(jobs|timing|rehearsal-report|summary-.+)\.json$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
# data/ and etl/ are restored from the capture base, then the pack.
# Code and every other tree stay on the commit under test.
_EXACT_PREFIXES = ("data", "etl")
_CANDIDATE_MANIFEST = "candidate-manifest.json"
SNAPSHOT_ONLY_NOTICE = (
    "notice: snapshot-only artifact; replay places the snapshot directory, not the captured data and etl tree"
)
NO_CANDIDATE_NOTICE = "notice: no rehearsal candidate with a live snapshot artifact; replay skipped"
# 40 covers the 14-day artifact window at a weekly cadence with room for reruns.
_RUN_LIST_LIMIT = 40


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


def _notice(line: str) -> None:
    print(f"::notice::{line}")
    _write_summary(line)


def _safe_rel(path: str) -> Path:
    """Reject a path that is not already a plain relative path, then return it.

    pathlib collapses "." before .parts (Python 3.14), so the raw segments are
    judged first. The returned path is what every write decision uses.
    """
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path or path.startswith("/"):
        raise SystemExit(f"unsafe candidate path {path}")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise SystemExit(f"unsafe candidate path {path}")
    normalised = posixpath.normpath(path)
    if normalised != path or normalised.startswith("/") or normalised.startswith(".."):
        raise SystemExit(f"unsafe candidate path {path}")
    rel = Path(normalised)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        raise SystemExit(f"unsafe candidate path {path}")
    return rel


def _covered(rel: Path) -> bool:
    """True when the normalised path is a file inside data/ or etl/."""
    return len(rel.parts) >= 2 and rel.parts[0] in _EXACT_PREFIXES


def _reject_symlink(anchor: Path, rel: Path) -> None:
    cursor = anchor
    for part in rel.parts:
        if cursor.is_symlink():
            raise SystemExit(f"unsafe candidate path {rel.as_posix()}")
        cursor = cursor / part
    if cursor.is_symlink():
        raise SystemExit(f"unsafe candidate path {rel.as_posix()}")


def _git(root: Path, *args: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_text, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SystemExit(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _candidate_manifests(download_dir: Path) -> list[Path]:
    return [path for path in download_dir.rglob(_CANDIDATE_MANIFEST) if path.is_file()]


def _packed_roots(manifests: list[Path]) -> list[Path]:
    return [path.parent / "files" for path in manifests]


def _under_packed(path: Path, roots: list[Path]) -> bool:
    return any(root == path or root in path.parents for root in roots)


def _nul_records(blob: str) -> list[str]:
    parts = blob.split("\0")
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def pack_candidate(root: Path, out_dir: Path) -> dict:
    """Pack every tracked path the capture changed, added or deleted. The list comes from git."""
    base = _git(root, "rev-parse", "HEAD").strip()
    if not _SHA.match(base):
        raise SystemExit(f"base commit is not a sha: {base}")
    diff = _nul_records(_git(root, "diff", "--name-status", "--no-renames", "-z", "HEAD"))
    entries: list[dict[str, str]] = []
    index = 0
    while index < len(diff):
        status = diff[index]
        if index + 1 >= len(diff):
            raise SystemExit("git diff --name-status -z ended on a status")
        path = diff[index + 1]
        index += 2
        letter = "D" if status.startswith("D") else "A" if status.startswith("A") else "M"
        entries.append({"path": path, "status": letter})
    for path in _nul_records(_git(root, "ls-files", "--others", "--exclude-standard", "-z")):
        entries.append({"path": path, "status": "A"})
    entries.sort(key=lambda item: item["path"])
    files_dir = out_dir / "files"
    if files_dir.exists():
        shutil.rmtree(files_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in entries:
        if item["status"] == "D":
            continue
        rel = _safe_rel(item["path"])
        source = root.joinpath(*rel.parts)
        if source.is_symlink() or not source.is_file():
            raise SystemExit(f"changed path is not a file: {item['path']}")
        dest = files_dir.joinpath(*rel.parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    manifest = {"base_sha": base, "paths": entries}
    (out_dir / _CANDIDATE_MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    base = manifest.get("base_sha")
    paths = manifest.get("paths")
    if not isinstance(base, str) or not _SHA.match(base):
        raise SystemExit("candidate manifest has no base_sha")
    if not isinstance(paths, list):
        raise SystemExit("candidate manifest has no paths")
    return manifest


def _has_commit(root: Path, sha: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{sha}^{{commit}}"],
        capture_output=True, check=False,
    )
    return result.returncode == 0


def _ls_tree(root: Path, rev: str, prefix: str) -> set[str]:
    return {line for line in _git(root, "ls-tree", "-r", "--name-only", rev, prefix).splitlines() if line}


def _plan_writes(paths: list) -> list[tuple[str, Path]]:
    """Validate every entry before any write. The normalised path decides coverage."""
    seen: set[str] = set()
    planned: list[tuple[str, Path]] = []
    for item in paths:
        if not isinstance(item, dict):
            raise SystemExit("candidate path entry is not an object")
        raw = item.get("path")
        status = item.get("status")
        if not isinstance(raw, str) or status not in {"A", "M", "D"}:
            raise SystemExit(f"bad candidate path entry {item!r}")
        rel = _safe_rel(raw)
        key = rel.as_posix()
        if key in seen:
            raise SystemExit(f"duplicate candidate path {key}")
        seen.add(key)
        if _covered(rel):
            planned.append((status, rel))
    return planned


def apply_candidate(root: Path, manifest_path: Path) -> None:
    """data/ and etl/ become the capture tree. Every other path stays at HEAD."""
    manifest = _load_manifest(manifest_path)
    base = manifest["base_sha"]
    if not _has_commit(root, base):
        raise SystemExit(f"base commit {base} is not in this checkout")
    planned = _plan_writes(manifest["paths"])
    head: set[str] = set()
    base_files: set[str] = set()
    for prefix in _EXACT_PREFIXES:
        head |= _ls_tree(root, "HEAD", prefix)
        base_files |= _ls_tree(root, base, prefix)
    extras = sorted(head - base_files)
    if extras:
        _git(root, "rm", "-q", "--ignore-unmatch", "--pathspec-from-file=-", "--pathspec-file-nul",
             input_text="\0".join(extras) + "\0")
    _git(root, "checkout", base, "--", *_EXACT_PREFIXES)
    files_dir = manifest_path.parent / "files"
    for status, rel in planned:
        _reject_symlink(root, rel)
        dest = root.joinpath(*rel.parts)
        if status == "D":
            if dest.is_file():
                dest.unlink()
            continue
        source = files_dir.joinpath(*rel.parts)
        _reject_symlink(files_dir, rel)
        if source.is_symlink() or not source.is_file():
            raise SystemExit(f"candidate pack is missing {rel.as_posix()}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            raise SystemExit(f"unsafe candidate path {rel.as_posix()}")
        shutil.copy2(source, dest)


def _snapshot_payload(download_dir: Path) -> tuple[Path, dict, str]:
    manifests = _candidate_manifests(download_dir)
    packed = _packed_roots(manifests)
    found = [path for path in download_dir.rglob("snapshot.json") if path.is_file() and not _under_packed(path, packed)]
    if not found:
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
    return chosen, payload, date


def _point_latest(data_dir: Path, payload: dict) -> None:
    # The site reads data/latest.json to pick its current snapshot; point it at the
    # candidate, keeping the pointer's own fields, as the collector would.
    latest = data_dir / "latest.json"
    pointer = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else {}
    keys = list(pointer) or ["snapshot_date", "period", "snapshot_id", "methodology_version"]
    latest.write_text(json.dumps({key: payload.get(key) for key in keys if key in payload or key == "snapshot_date"},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _copy_summary(download_dir: Path, summary_dir: Path | None) -> None:
    if summary_dir is None:
        return
    summary = next((path for path in download_dir.rglob("summary-graphql.json")
                    if path.is_file() and not _under_packed(path, _packed_roots(_candidate_manifests(download_dir)))), None)
    if summary is None:
        return
    summary_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(summary, summary_dir / "summary-graphql.json")


def _export_date(date: str) -> None:
    env_path = os.environ.get("GITHUB_ENV")
    if env_path:
        with open(env_path, "a", encoding="utf-8") as stream:
            stream.write(f"SNAPSHOT_DATE={date}\n")


def _place_snapshot_only(chosen: Path, payload: dict, date: str, data_dir: Path) -> None:
    dest = data_dir / "snapshots" / date
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for item in chosen.parent.iterdir():
        if item.is_file() and not _SUMMARY_FILE.match(item.name):
            shutil.copy2(item, dest / item.name)
    _point_latest(data_dir, payload)


def place_replay(download_dir: Path, data_dir: Path, summary_dir: Path | None = None,
                 root: Path | None = None) -> str:
    manifests = _candidate_manifests(download_dir)
    if len(manifests) > 1:
        raise SystemExit("artifact contains more than one candidate-manifest.json")
    chosen, payload, date = _snapshot_payload(download_dir)
    if not manifests:
        _notice(SNAPSHOT_ONLY_NOTICE)
        _place_snapshot_only(chosen, payload, date, data_dir)
    else:
        apply_candidate(root or Path("."), manifests[0])
    _copy_summary(download_dir, summary_dir)
    _export_date(date)
    print(date)
    return date


def _is_rehearsal_run(run: dict) -> bool:
    title = str(run.get("displayTitle") or run.get("display_title") or "")
    if not title.startswith("weekly rehearsal"):
        return False
    status = run.get("status")
    return status in (None, "completed")


def select_source(runs: list[dict], artifact_live) -> int | None:
    """Newest completed rehearsal run whose snapshot artifact is still live."""
    for run in runs:
        if not _is_rehearsal_run(run):
            continue
        raw = run.get("databaseId", run.get("id"))
        if raw is None:
            continue
        run_id = int(raw)
        if artifact_live(run_id):
            return run_id
    return None


def _weekly_runs() -> list[dict]:
    raw = subprocess.check_output([
        "gh", "run", "list",
        "--workflow", "weekly-snapshot.yml",
        "--branch", "main",
        "--limit", str(_RUN_LIST_LIMIT),
        "--json", "databaseId,displayTitle,status,conclusion",
    ], text=True)
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise SystemExit("gh run list did not return a list")
    return payload


def _snapshot_artifact_live(run_id: int) -> bool:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is not set")
    raw = subprocess.check_output([
        "gh", "api", f"repos/{repo}/actions/runs/{run_id}/artifacts",
    ], text=True)
    body = json.loads(raw)
    for artifact in body.get("artifacts") or []:
        name = str(artifact.get("name") or "")
        if name.startswith("snapshot-") and not artifact.get("expired"):
            return True
    return False


def _write_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(f"{name}={value}\n")


def select_replay() -> int:
    source = os.environ.get("SOURCE_RUN", "").strip()
    if source:
        _write_output("found", "true")
        _write_output("run_id", source)
        print(source)
        return 0
    chosen = select_source(_weekly_runs(), _snapshot_artifact_live)
    if chosen is None:
        _notice(NO_CANDIDATE_NOTICE)
        _write_output("found", "false")
        return 0
    _write_output("found", "true")
    _write_output("run_id", str(chosen))
    print(chosen)
    return 0


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
             if key not in {expected, "report", *ALSO_CATCHES.get(drill, set())}
             and outcomes.get(key) == "failure"]
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
    place.add_argument("--root", type=Path, default=Path("."))

    pack = commands.add_parser("pack")
    pack.add_argument("--out", type=Path, required=True)
    pack.add_argument("--root", type=Path, default=Path("."))

    apply = commands.add_parser("apply")
    apply.add_argument("--drill", required=True)
    apply.add_argument("--date", default=os.environ.get("SNAPSHOT_DATE"))
    apply.add_argument("--root", type=Path, default=Path("."))

    commands.add_parser("select")
    commands.add_parser("verdict")
    args = parser.parse_args(argv)
    if args.cmd == "place":
        place_replay(args.download, args.data_dir, args.summary_dir, args.root)
        return 0
    if args.cmd == "pack":
        pack_candidate(args.root, args.out)
        return 0
    if args.cmd == "select":
        return select_replay()
    if args.cmd == "apply":
        apply_drill(args.root, args.drill, args.date)
        return 0
    outcomes = {key: os.environ.get(key.upper(), "skipped") for key, _name in CHECK_STEPS}
    line, code = drill_verdict(os.environ.get("DRILL", ""), outcomes)
    _write_summary(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
