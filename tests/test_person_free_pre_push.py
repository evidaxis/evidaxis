"""pre-push runs the new-bytes guard on the commits being pushed.

The login is invented. Without an index the hook warns and allows the push.
A null switch date stays dormant.
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


def _init(tmp_path: Path, switch_date: str | None) -> tuple[Path, Path, Path]:
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
        "pre_switch_commit": None if switch_date is None else base,
    }), encoding="utf-8")
    index = tmp_path / "index"
    index.mkdir()
    (index / "index.json").write_text(json.dumps({
        "schema": "person_index_1",
        "salt": "test-salt",
        "logins": [LOGIN],
        "allow": [],
    }), encoding="utf-8")
    remote = tmp_path / "remote.git"
    _git(repo, "init", "--bare", "-q", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    return repo, index, remote


def _env(index: Path | None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "EVX_PERSON_INDEX_DIR"}
    env["GIT_TERMINAL_PROMPT"] = "0"
    if index is not None:
        env["EVX_PERSON_INDEX_DIR"] = str(index)
    return env


def _push(repo: Path, index: Path | None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", f"core.hooksPath={HOOKS}", "push", "origin", "HEAD:refs/heads/main"],
        cwd=repo, env=_env(index), capture_output=True, text=True,
    )


def _commit_address(repo: Path) -> None:
    path = repo / "data" / "snapshots" / SWITCH / "snapshot.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"github_repo": ADDRESS}) + "\n", encoding="utf-8")
    _git(repo, "add", "data")
    _git(repo, "commit", "-q", "-m", f"record {ADDRESS}")


def test_pre_push_rejects_an_invented_login(tmp_path: Path) -> None:
    repo, index, remote = _init(tmp_path, SWITCH)
    first = _push(repo, index)
    assert first.returncode == 0, first.stderr
    base = _git(remote, "rev-parse", "refs/heads/main").stdout.strip()
    _commit_address(repo)
    rejected = _push(repo, index)
    assert rejected.returncode != 0
    assert LOGIN not in rejected.stdout and LOGIN not in rejected.stderr
    assert ADDRESS not in rejected.stdout and ADDRESS not in rejected.stderr
    assert _git(remote, "rev-parse", "refs/heads/main").stdout.strip() == base


def test_pre_push_warns_when_the_index_is_absent(tmp_path: Path) -> None:
    repo, _index, remote = _init(tmp_path, SWITCH)
    _commit_address(repo)
    result = _push(repo, None)
    assert result.returncode == 0, result.stderr
    assert "no local index; skipping" in result.stderr
    assert LOGIN not in result.stdout and LOGIN not in result.stderr
    assert _git(remote, "rev-parse", "--verify", "refs/heads/main").returncode == 0


def test_pre_push_is_dormant_while_the_switch_is_null(tmp_path: Path) -> None:
    repo, index, remote = _init(tmp_path, None)
    _commit_address(repo)
    result = _push(repo, index)
    assert result.returncode == 0, result.stderr
    assert "dormant" in result.stdout + result.stderr
    assert LOGIN not in result.stdout and LOGIN not in result.stderr
    assert _git(remote, "rev-parse", "--verify", "refs/heads/main").returncode == 0
