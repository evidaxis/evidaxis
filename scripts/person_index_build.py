#!/usr/bin/env python3
"""Build the person index for one run, then leave it only in that run's temp dir.

person_free_new_bytes.py reads index.json from EVX_PERSON_INDEX_DIR. This
script writes that file into the directory given by --out. It refuses a
directory inside the repository: the index lists personal logins and must
not be committed or cached.

Sources, both local files, never the network:
  git show <pre-switch commit>:etl/owner_types.json
  git show <pre-switch commit>:etl/project_accounts.json  (optional)
  --owners, a saved GitHub GraphQL nodes(ids:) response, a REST repository
  payload, or a gh_graphql cache file.

A User login is personal. An Organization login is not. A login listed in
project_accounts.json is a project account, so it is not personal either.
Stdout is a count. The logins are not printed.

    python3 scripts/person_index_build.py --out DIR --pre-switch-commit SHA --owners FILE [--repo DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
from pathlib import Path

_LOGIN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?")
_COMMIT = re.compile(r"[0-9a-fA-F]{7,64}")
_OWNER_TYPES = {"User", "Organization"}


class BuildError(Exception):
    """A safe message. It never includes a login or a file body."""


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False)
    except OSError as exc:
        raise BuildError("registry unreadable") from exc


def git_root(start: Path | None) -> Path:
    if start is not None:
        return start
    proc = _run_git(Path("."), "rev-parse", "--show-toplevel")
    if proc.returncode != 0 or not proc.stdout.strip():
        raise BuildError("registry unreadable")
    return Path(os.fsdecode(proc.stdout.strip()))


def _show(repo: Path, commit: str, path: str) -> bytes | None:
    """Return the blob, or None when that path is not in the commit."""
    proc = _run_git(repo, "show", f"{commit}:{path}")
    if proc.returncode == 0:
        return proc.stdout
    err = proc.stderr.decode("utf-8", "replace")
    # "does not exist in" and "exists on disk, but not in" are both absence.
    if "not in" in err or "does not exist" in err:
        return None
    raise BuildError("registry unreadable")


def _load_json(raw: bytes | None, label: str) -> dict | list | None:
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(label) from exc


def _login(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if _LOGIN.fullmatch(text) is None:
        return None
    return text


def _login_from_full_name(value: object) -> str | None:
    if not isinstance(value, str) or "/" not in value:
        return None
    return _login(value.split("/", 1)[0])


def project_logins(document: dict | list | None) -> set[str]:
    if document is None:
        return set()
    if not isinstance(document, dict) or not isinstance(document.get("accounts"), dict):
        raise BuildError("project accounts unreadable")
    found: set[str] = set()
    for key in document["accounts"]:
        login = _login(key)
        if login is None:
            raise BuildError("project accounts unreadable")
        found.add(login)
    return found


def registry_logins(document: dict | list | None, projects: set[str]) -> set[str]:
    if not isinstance(document, dict) or not isinstance(document.get("repos"), dict):
        raise BuildError("registry unreadable")
    found: set[str] = set()
    for key, entry in document["repos"].items():
        if not isinstance(entry, dict) or entry.get("owner_type") not in _OWNER_TYPES:
            raise BuildError("registry unreadable")
        if entry["owner_type"] != "User":
            continue
        login = _login_from_full_name(entry.get("full_name")) or _login_from_full_name(key)
        if login is None:
            raise BuildError("registry unreadable")
        if login not in projects:
            found.add(login)
    return found


def _nodes(document: dict | list) -> list:
    if isinstance(document, list):
        return document
    if not isinstance(document, dict):
        raise BuildError("owners unreadable")
    data = document.get("data")
    if isinstance(data, dict) and "nodes" in data:
        nodes = data["nodes"]
        if not isinstance(nodes, list):
            raise BuildError("owners unreadable")
        return nodes
    repos = document.get("repos")
    if isinstance(repos, dict):
        return list(repos.values())
    if {"full_name", "nameWithOwner", "owner", "owner_type"} & set(document):
        return [document]
    raise BuildError("owners unreadable")


def _node_login(node: dict) -> tuple[str, str]:
    owner = node.get("owner") if isinstance(node.get("owner"), dict) else {}
    owner_type = node.get("owner_type") or owner.get("__typename") or owner.get("type")
    if owner_type not in _OWNER_TYPES:
        raise BuildError("owners unreadable")
    login = _login(owner.get("login"))
    if login is None:
        login = _login_from_full_name(node.get("nameWithOwner")) or _login_from_full_name(node.get("full_name"))
    if login is None:
        raise BuildError("owners unreadable")
    return login, owner_type


def current_logins(document: dict | list | None, projects: set[str]) -> set[str]:
    if document is None:
        raise BuildError("owners unreadable")
    found: set[str] = set()
    for node in _nodes(document):
        if node is None:
            continue
        if not isinstance(node, dict):
            raise BuildError("owners unreadable")
        login, owner_type = _node_login(node)
        if owner_type == "User" and login not in projects:
            found.add(login)
    return found


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def write_index(directory: Path, repo: Path, logins: set[str], salt: str | None = None) -> Path:
    if _inside(directory, repo):
        raise BuildError("index must stay outside the repository")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BuildError("output unavailable") from exc
    # 0700: the directory holds personal logins and lives only for this run.
    directory.chmod(0o700)
    payload = {
        "schema": "person_index_1",
        "salt": salt or secrets.token_hex(32),
        "logins": sorted(logins),
        "allow": [],
    }
    body = (json.dumps(payload, indent=2) + "\n").encode()
    target = directory / "index.json"
    temporary = directory / ".index.json.tmp"
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            view = memoryview(body)
            while view:
                view = view[os.write(fd, view):]
        finally:
            os.close(fd)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    except OSError as exc:
        raise BuildError("output unavailable") from exc
    return target


def build(repo: Path, commit: str, owners_path: Path, out: Path) -> int:
    if _COMMIT.fullmatch(commit) is None:
        raise BuildError("pre-switch commit required")
    registry = _load_json(_show(repo, commit, "etl/owner_types.json"), "registry unreadable")
    projects = project_logins(_load_json(_show(repo, commit, "etl/project_accounts.json"), "project accounts unreadable"))
    try:
        owners_raw = owners_path.read_bytes()
    except OSError as exc:
        raise BuildError("owners unreadable") from exc
    owners = _load_json(owners_raw, "owners unreadable")
    logins = registry_logins(registry, projects) | current_logins(owners, projects)
    write_index(out, repo, logins)
    print(f"person index: {len(logins)} logins")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="person_index_build.py")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pre-switch-commit", required=True)
    parser.add_argument("--owners", type=Path, required=True)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args(argv)
    try:
        return build(git_root(args.repo), args.pre_switch_commit, args.owners, args.out)
    except BuildError as exc:
        print(f"person index: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
