"""The new-bytes guard fails on an invented personal address after the switch.

The login is a fixture. It is not in the owner registry. A dated folder from
before the switch is out of scope, and a null switch date does nothing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "person_free_new_bytes.py"
LOGIN = "zznotaperson99"
SWITCH = "2026-11-21"
ADDRESS = f"{LOGIN}/widget"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _init(tmp_path: Path, switch_date: str | None, commit: str | None = "") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    hooks = tmp_path / "no-hooks"
    hooks.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "evx-test@example.com")
    _git(repo, "config", "user.name", "evx-test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", str(hooks))
    (repo / "README").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    scripts = repo / "scripts"
    scripts.mkdir()
    pre = None if commit == "" else commit
    if commit == "":
        pre = base
    (scripts / "person_free_switch.json").write_text(json.dumps({
        "switch_date": switch_date,
        "pre_switch_commit": pre,
    }), encoding="utf-8")
    return repo


def _index(tmp_path: Path) -> Path:
    directory = tmp_path / "index"
    directory.mkdir()
    (directory / "index.json").write_text(json.dumps({
        "schema": "person_index_1",
        "salt": "test-salt",
        "logins": [LOGIN],
        "allow": [],
    }), encoding="utf-8")
    return directory


def _commit_file(repo: Path, relative: str, text: str, message: str = "add file") -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", "--", relative)
    _git(repo, "commit", "-q", "-m", message)


def _run(repo: Path, index: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "EVX_PERSON_INDEX_DIR"}
    if index is not None:
        env["EVX_PERSON_INDEX_DIR"] = str(index)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo, env=env, capture_output=True, text=True,
    )


def test_snapshot_on_switch_date_is_a_finding(tmp_path: Path) -> None:
    repo = _init(tmp_path, SWITCH)
    _commit_file(repo, f"data/snapshots/{SWITCH}/snapshot.json", json.dumps({"github_repo": ADDRESS}) + "\n")
    result = _run(repo, _index(tmp_path))
    assert result.returncode == 1
    assert f"data/snapshots/{SWITCH}/snapshot.json:" in result.stdout
    assert LOGIN not in result.stdout and LOGIN not in result.stderr


def test_observation_and_entity_changed_after_switch_are_findings(tmp_path: Path) -> None:
    repo = _init(tmp_path, SWITCH)
    _commit_file(
        repo,
        f"data/observations/{SWITCH}/observations.jsonl",
        json.dumps({"github_repo": ADDRESS}) + "\n",
    )
    _commit_file(repo, "entities/e_0123456789A.md", f"homepage: https://github.com/{ADDRESS}\n")
    result = _run(repo, _index(tmp_path))
    assert result.returncode == 1
    assert f"data/observations/{SWITCH}/observations.jsonl:" in result.stdout
    assert "entities/e_0123456789A.md:" in result.stdout
    assert LOGIN not in result.stdout and LOGIN not in result.stderr


def test_commit_message_is_a_finding(tmp_path: Path) -> None:
    repo = _init(tmp_path, SWITCH)
    _commit_file(repo, "notes.txt", "clean\n", message=f"record {ADDRESS}")
    result = _run(repo, _index(tmp_path))
    assert result.returncode == 1
    assert "commit:" in result.stdout
    assert LOGIN not in result.stdout and LOGIN not in result.stderr


def test_percent_encoded_address_is_a_finding(tmp_path: Path) -> None:
    repo = _init(tmp_path, SWITCH)
    encoded = "https://github.com%2F" + LOGIN + "%2Fwidget"
    _commit_file(repo, f"data/snapshots/{SWITCH}/snapshot.json", json.dumps({"homepage": encoded}) + "\n")
    result = _run(repo, _index(tmp_path))
    assert result.returncode == 1
    assert LOGIN not in result.stdout and LOGIN not in result.stderr


def test_login_is_absent_from_guard_output(tmp_path: Path) -> None:
    repo = _init(tmp_path, SWITCH)
    _commit_file(repo, f"data/snapshots/{SWITCH}/snapshot.json", json.dumps({"github_repo": ADDRESS}) + "\n")
    result = _run(repo, _index(tmp_path))
    assert result.returncode == 1
    assert ADDRESS not in result.stdout and ADDRESS not in result.stderr
    assert LOGIN not in result.stdout and LOGIN not in result.stderr
    assert "rule " in result.stdout


def test_dated_file_before_switch_is_clean(tmp_path: Path) -> None:
    repo = _init(tmp_path, SWITCH)
    _commit_file(repo, "data/snapshots/2026-10-17/snapshot.json", json.dumps({"github_repo": ADDRESS}) + "\n")
    result = _run(repo, _index(tmp_path))
    assert result.returncode == 0
    assert result.stdout == "person-free new bytes: 0 findings\n"
    assert LOGIN not in result.stderr


def test_null_switch_is_dormant_and_missing_index_is_required(tmp_path: Path) -> None:
    repo = _init(tmp_path, None, commit=None)
    _commit_file(repo, f"data/snapshots/{SWITCH}/snapshot.json", json.dumps({"github_repo": ADDRESS}) + "\n")
    dormant = _run(repo, _index(tmp_path), "--require-index")
    assert dormant.returncode == 0
    assert dormant.stdout == "person-free new bytes: dormant\n"
    assert LOGIN not in dormant.stderr

    (repo / "scripts" / "person_free_switch.json").write_text(json.dumps({
        "switch_date": SWITCH,
        "pre_switch_commit": _git(repo, "rev-parse", "HEAD~1").stdout.strip(),
    }), encoding="utf-8")
    missing = _run(repo, None, "--require-index")
    assert missing.returncode == 2
    assert missing.stdout == "person-free new bytes: index required\n"

    skipped = _run(repo, None)
    assert skipped.returncode == 0
    assert skipped.stdout == "person-free new bytes: skipped\n"


def test_directory_scan_finds_an_address(tmp_path: Path) -> None:
    repo = _init(tmp_path, SWITCH)
    artifact = tmp_path / "artifact"
    target = artifact / "snapshot.json"
    target.parent.mkdir()
    target.write_text(json.dumps({"github_repo": ADDRESS}) + "\n", encoding="utf-8")
    result = _run(repo, _index(tmp_path), "--dir", str(artifact))
    assert result.returncode == 1
    assert "snapshot.json:" in result.stdout
    assert LOGIN not in result.stdout and LOGIN not in result.stderr


def test_privacy_gate_job_is_dormant_and_skips_forks() -> None:
    workflow = yaml.safe_load((REPO / ".github/workflows/privacy-gate.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["person-free-new-bytes"]
    command = "\n".join(step.get("run", "") for step in job["steps"])
    assert "scripts/person_free_new_bytes.py" in command
    assert "--require-index" in command
    assert "head.repo.full_name" in job["if"]
    assert "refs/heads/main" in job["if"]
    assert workflow["jobs"]["owner-traces"]["steps"][-1]["run"] == "python3 scripts/owner_trace_check.py"
    switch = json.loads((REPO / "scripts/person_free_switch.json").read_text(encoding="utf-8"))
    assert switch == {"switch_date": None, "pre_switch_commit": None}
