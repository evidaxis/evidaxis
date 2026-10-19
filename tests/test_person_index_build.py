"""The run index is built from fixture files. It is not written into the repo.

The logins are invented. A test below checks that none of them occur in
etl/owner_types.json. The builder does not open a network connection.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "person_index_build.py"
GUARD = REPO / "scripts" / "person_free_new_bytes.py"
PERSON = "zznotaperson99"
CURRENT = "zzformerperson99"
ORG = "zzorgfixture99"
PROJECT = "zzprojectfixture99"
FIXTURES = (PERSON, CURRENT, ORG, PROJECT)
SWITCH = "2026-11-21"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _init(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    hooks = tmp_path / "no-hooks"
    hooks.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "evx-test@example.com")
    _git(repo, "config", "user.name", "evx-test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", str(hooks))
    etl = repo / "etl"
    etl.mkdir()
    (etl / "owner_types.json").write_text(json.dumps({
        "schema_version": "owner_types_1",
        "repos": {
            f"{PERSON}/widget": {"full_name": f"{PERSON}/widget", "owner_type": "User", "repo_id": 900001},
            f"{ORG}/widget": {"full_name": f"{ORG}/widget", "owner_type": "Organization", "repo_id": 900002},
            f"{PROJECT}/widget": {"full_name": f"{PROJECT}/widget", "owner_type": "User", "repo_id": 900003},
        },
    }), encoding="utf-8")
    (etl / "project_accounts.json").write_text(json.dumps({
        "schema_version": "project_accounts_1",
        "accounts": {PROJECT: {"repo": f"{PROJECT}/widget"}},
    }), encoding="utf-8")
    _git(repo, "add", "etl")
    _git(repo, "commit", "-q", "-m", "registry")
    return repo


def _owners(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "owners.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _build(repo: Path, owners: Path, out: Path) -> subprocess.CompletedProcess[str]:
    commit = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--out", str(out),
         "--pre-switch-commit", commit, "--owners", str(owners)],
        capture_output=True, text=True,
    )


def _guard(repo: Path, index: Path, relative: str, text: str) -> subprocess.CompletedProcess[str]:
    commit = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "scripts").mkdir(exist_ok=True)
    (repo / "scripts" / "person_free_switch.json").write_text(json.dumps({
        "switch_date": SWITCH,
        "pre_switch_commit": commit,
    }), encoding="utf-8")
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", "--", relative)
    _git(repo, "commit", "-q", "-m", "snapshot")
    env = {key: value for key, value in os.environ.items() if key != "EVX_PERSON_INDEX_DIR"}
    env["EVX_PERSON_INDEX_DIR"] = str(index)
    return subprocess.run(
        [sys.executable, str(GUARD)],
        cwd=repo, env=env, capture_output=True, text=True,
    )


def test_fixture_logins_are_absent_from_the_real_registry() -> None:
    text = (REPO / "etl" / "owner_types.json").read_text(encoding="utf-8").lower()
    for login in FIXTURES:
        assert login not in text


def test_registry_and_current_personal_logins_are_indexed(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    owners = _owners(tmp_path, {"data": {"nodes": [
        {"nameWithOwner": f"{CURRENT}/widget", "databaseId": 900004,
         "owner": {"login": CURRENT, "__typename": "User"}},
        {"nameWithOwner": f"{ORG}/other", "databaseId": 900005,
         "owner": {"login": ORG, "__typename": "Organization"}},
        None,
    ]}})
    out = tmp_path / "index"
    built = _build(repo, owners, out)
    assert built.returncode == 0, built.stderr
    for login in FIXTURES:
        assert login not in built.stdout and login not in built.stderr
    document = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert document["schema"] == "person_index_1"
    assert set(document["logins"]) == {PERSON, CURRENT}

    personal = _guard(repo, out, f"data/snapshots/{SWITCH}/one.json", json.dumps({"github_repo": f"{PERSON}/widget"}) + "\n")
    current = _guard(repo, out, f"data/snapshots/{SWITCH}/two.json", json.dumps({"github_repo": f"{CURRENT}/widget"}) + "\n")
    assert personal.returncode == 1
    assert current.returncode == 1
    for login in FIXTURES:
        assert login not in personal.stdout and login not in personal.stderr
        assert login not in current.stdout and login not in current.stderr


def test_organization_and_project_account_are_not_indexed(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    owners = _owners(tmp_path, {"data": {"nodes": []}})
    out = tmp_path / "index"
    built = _build(repo, owners, out)
    assert built.returncode == 0, built.stderr
    document = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert ORG not in document["logins"]
    assert PROJECT not in document["logins"]
    org = _guard(repo, out, f"data/snapshots/{SWITCH}/org.json", json.dumps({"github_repo": f"{ORG}/widget"}) + "\n")
    project = _guard(repo, out, f"data/snapshots/{SWITCH}/project.json", json.dumps({"github_repo": f"{PROJECT}/widget"}) + "\n")
    assert org.returncode == 0
    assert project.returncode == 0


def test_rest_owner_payload_is_indexed(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    owners = _owners(tmp_path, [{
        "id": 900006,
        "full_name": f"{CURRENT}/widget",
        "owner": {"login": CURRENT, "type": "User"},
    }])
    out = tmp_path / "index"
    built = _build(repo, owners, out)
    assert built.returncode == 0, built.stderr
    document = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert CURRENT in document["logins"]
    assert PERSON in document["logins"]


def test_refuses_to_write_the_index_inside_the_repository(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    owners = _owners(tmp_path, {"data": {"nodes": []}})
    inside = repo / "run-index"
    built = _build(repo, owners, inside)
    assert built.returncode == 2
    assert "outside the repository" in built.stdout
    assert not (inside / "index.json").exists()
    for login in FIXTURES:
        assert login not in built.stdout and login not in built.stderr
