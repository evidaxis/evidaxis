"""Local commit hooks run the new-bytes guard on an invented login.

Without EVX_PERSON_INDEX_DIR the hook warns and allows the commit.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / "scripts" / "hooks"
LOGIN = "zznotaperson99"
ADDRESS = f"{LOGIN}/widget"
SWITCH = "2026-11-21"


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=True)


def _init(tmp_path: Path, switch_date: str | None) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    quiet = tmp_path / "no-hooks"
    quiet.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "evx-test@example.com")
    _git(repo, "config", "user.name", "evx-test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", str(quiet))
    (repo / "README").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    scripts = repo / "scripts"
    scripts.mkdir()
    (scripts / "person_free_switch.json").write_text(json.dumps({
        "switch_date": switch_date,
        "pre_switch_commit": base,
    }), encoding="utf-8")
    index = tmp_path / "index"
    index.mkdir()
    (index / "index.json").write_text(json.dumps({
        "schema": "person_index_1",
        "salt": "test-salt",
        "logins": [LOGIN],
        "allow": [],
    }), encoding="utf-8")
    return repo, index


def _commit(repo: Path, message: str, index: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "EVX_PERSON_INDEX_DIR"}
    if index is not None:
        env["EVX_PERSON_INDEX_DIR"] = str(index)
    return subprocess.run(
        ["git", "-c", f"core.hooksPath={HOOKS}", "commit", "-m", message, *args],
        cwd=repo, env=env, capture_output=True, text=True,
    )


def test_pre_commit_rejects_a_staged_address(tmp_path: Path) -> None:
    repo, index = _init(tmp_path, SWITCH)
    path = repo / "data" / "snapshots" / SWITCH / "snapshot.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"github_repo": ADDRESS}) + "\n", encoding="utf-8")
    _git(repo, "add", "data")
    result = _commit(repo, "add snapshot", index)
    assert result.returncode != 0
    assert LOGIN not in result.stdout and LOGIN not in result.stderr
    assert "add snapshot" not in _git(repo, "log", "--oneline").stdout


def test_commit_msg_rejects_an_address(tmp_path: Path) -> None:
    repo, index = _init(tmp_path, SWITCH)
    result = _commit(repo, f"record {ADDRESS}", index, "--allow-empty")
    assert result.returncode != 0
    assert LOGIN not in result.stdout and LOGIN not in result.stderr
    assert _git(repo, "rev-list", "--count", "HEAD").stdout.strip() == "1"


def test_hooks_skip_when_the_index_is_absent(tmp_path: Path) -> None:
    repo, _index = _init(tmp_path, SWITCH)
    path = repo / "notes.txt"
    path.write_text(ADDRESS + "\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    result = _commit(repo, f"record {ADDRESS}", None)
    assert result.returncode == 0
    # Both hooks run on this commit, and each one has to warn on its own.
    assert result.stderr.count("no local index; skipping") == 2
    assert LOGIN not in result.stderr


def test_hooks_allow_a_clean_commit(tmp_path: Path) -> None:
    repo, index = _init(tmp_path, SWITCH)
    (repo / "notes.txt").write_text("nothing personal\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    result = _commit(repo, "notes", index)
    assert result.returncode == 0
    assert _git(repo, "log", "-1", "--format=%s").stdout.strip() == "notes"


def test_hooks_stay_dormant_while_the_switch_is_null(tmp_path: Path) -> None:
    repo, index = _init(tmp_path, None)
    path = repo / "data" / "snapshots" / SWITCH / "snapshot.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"github_repo": ADDRESS}) + "\n", encoding="utf-8")
    _git(repo, "add", "data")
    result = _commit(repo, "record a snapshot", index)
    assert result.returncode == 0
    assert "dormant" in result.stdout + result.stderr
