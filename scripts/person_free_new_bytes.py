#!/usr/bin/env python3
"""Fail when a new published byte contains a personal account login.

The switch date lives in scripts/person_free_switch.json. While it is null
or the file is absent, the check prints "dormant" and exits 0: privacy-gate
can run it on every push without blocking the release chain.

Logins come only from the directory in EVX_PERSON_INDEX_DIR (index.json).
Output is a path, a line number, a rule number and 8 hex characters of a
salted hash. The login and the address are never printed, because the log
of a public repository is visible to any signed-in GitHub user.

Exit 1: findings. Exit 2: error, or no index when --require-index is set.
Exit 0: clean, dormant, or "skipped" when the index is absent and was not
required (a fork has no index).

    python3 scripts/person_free_new_bytes.py [--require-index] [base [head]]
    python3 scripts/person_free_new_bytes.py --staged
    python3 scripts/person_free_new_bytes.py --dir DIR
    python3 scripts/person_free_new_bytes.py --message-file PATH
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.person_free import (
    GH_PAGES,
    GH_PROFILE,
    GH_RAW,
    MENTION,
    SLUG,
    WORD,
    build_handle_index,
    lenient_decoded,
)

# Rule numbers are part of the public diagnostic. They name the shape, never the login.
RULE_PREFIX = 1
RULE_MENTION = 2
RULE_GITHUB = 3
RULE_PAGES = 4
RULE_RAW = 5
RULE_EXACT = 6
RULE_WORD = 7

_JSON_STRING = re.compile(r'"((?:\\.|[^"\\])*)"')
_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


class ScanError(Exception):
    """A scan that cannot be trusted. The message is safe to print."""


def salted(salt: str, *parts: str) -> str:
    return hashlib.sha256(("\n".join((salt, *parts))).encode()).hexdigest()


def load_switch(root: Path) -> tuple[date, str] | None:
    """None means dormant: missing file, or switch_date null.

    A set date with a missing pre_switch_commit is still returned; the range
    scan rejects it later. Staged, directory and message scans do not need it.
    """
    path = root / "scripts" / "person_free_switch.json"
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScanError("switch config unreadable") from exc
    if not isinstance(document, dict) or set(document) != {"switch_date", "pre_switch_commit"}:
        raise ScanError("switch config schema")
    raw_date = document["switch_date"]
    if raw_date is None:
        return None
    if not isinstance(raw_date, str) or date_from(raw_date) is None:
        raise ScanError("switch config schema")
    commit = document["pre_switch_commit"]
    if commit is not None and (not isinstance(commit, str) or not commit.strip() or any(c.isspace() for c in commit)):
        raise ScanError("switch config schema")
    return date_from(raw_date), commit


def date_from(value: str) -> date | None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def path_before_switch(path: str, switch: date) -> bool:
    """Dated archive folders from before the switch keep their bytes (invariant 4).

    A YYYY-MM folder is before the switch only when the whole month is: a folder
    for the switch month can hold both old and new days, so it stays in the scan.
    """
    for part in path.split("/"):
        day = _DAY.fullmatch(part)
        if day:
            found = date_from(part)
            if found is not None and found < switch:
                return True
            continue
        month = _MONTH.fullmatch(part)
        if month:
            year, month_number = int(month.group(1)), int(month.group(2))
            if 1 <= month_number <= 12 and (year, month_number) < (switch.year, switch.month):
                return True
    return False


def load_index(directory: Path | None, *, required: bool) -> tuple[str, frozenset[str], frozenset[str]] | None:
    """Return (salt, logins, allow) or None when the index is absent and optional."""
    if directory is None or not directory.is_dir() or not (directory / "index.json").is_file():
        if required:
            raise ScanError("index required")
        return None
    try:
        document = json.loads((directory / "index.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScanError("index unreadable") from exc
    if not isinstance(document, dict) or set(document) - {"schema", "salt", "logins", "allow"}:
        raise ScanError("index schema")
    if document.get("schema") != "person_index_1":
        raise ScanError("index schema")
    salt = document.get("salt")
    logins = document.get("logins")
    allow = document.get("allow", [])
    if not isinstance(salt, str) or not salt:
        raise ScanError("index schema")
    if not isinstance(logins, list) or not all(isinstance(item, str) and item.strip() for item in logins):
        raise ScanError("index schema")
    if not isinstance(allow, list) or not all(isinstance(item, str) and re.fullmatch(r"[0-9a-f]{64}", item) for item in allow):
        raise ScanError("index schema")
    return salt, frozenset(item.strip().lower() for item in logins), frozenset(allow)


def git_root() -> Path:
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, check=False)
    except OSError as exc:
        raise ScanError("git scan failed") from exc
    if proc.returncode != 0 or not proc.stdout.strip():
        raise ScanError("git scan failed")
    return Path(os.fsdecode(proc.stdout.strip()))


def git_bytes(root: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    except OSError as exc:
        raise ScanError("git scan failed") from exc
    if proc.returncode != 0:
        raise ScanError("git scan failed")
    return proc.stdout


def git_names(root: Path, *args: str) -> list[str]:
    raw = git_bytes(root, *args)
    return [os.fsdecode(part) for part in raw.split(b"\0") if part]


def match_piece(text: str, index) -> list[tuple[int, str]]:
    """Shapes from section 6, using the person_free expressions.

    Prefix, mention and the three GitHub forms count for every indexed login.
    A whole value equal to a login counts even when it is short. A standalone
    word counts only for the distinctive logins person_free already selects.
    """
    decoded = lenient_decoded(text).lower()
    found: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    def add(rule: int, login: str) -> None:
        if login in index.all and (rule, login) not in seen:
            seen.add((rule, login))
            found.append((rule, login))

    for match in SLUG.finditer(decoded):
        add(RULE_PREFIX, match.group(1))
    for match in MENTION.finditer(decoded):
        add(RULE_MENTION, match.group(1))
    for match in GH_PROFILE.finditer(decoded):
        add(RULE_GITHUB, match.group(1))
    for match in GH_PAGES.finditer(decoded):
        add(RULE_PAGES, match.group(1))
    for match in GH_RAW.finditer(decoded):
        add(RULE_RAW, match.group(1))
    stripped = decoded.strip()
    if stripped in index.all:
        add(RULE_EXACT, stripped)
    for match in _JSON_STRING.finditer(decoded):
        try:
            value = json.loads(f'"{match.group(1)}"')
        except json.JSONDecodeError:
            continue
        if isinstance(value, str) and value.strip().lower() in index.all:
            add(RULE_EXACT, value.strip().lower())
    for match in WORD.finditer(decoded):
        token = match.group(0)
        if token in index.words:
            add(RULE_WORD, token)
    return found


def scan_text(text: str, index) -> list[tuple[int, int, str]]:
    findings: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int, str]] = set()
    for number, line in enumerate(text.splitlines(), 1):
        # Decode the line, then each piece: a %0A inside one published line
        # must not hide an address on the far side of the encoded break.
        for piece in lenient_decoded(line).splitlines() or [""]:
            for rule, login in match_piece(piece, index):
                key = (number, rule, login)
                if key not in seen:
                    seen.add(key)
                    findings.append(key)
    return findings


def text_of(raw: bytes) -> str:
    return raw.decode("utf-8", "surrogateescape")


def public_label(label: str, logins: frozenset[str]) -> str:
    lower = label.lower()
    if any(login in lower for login in logins):
        # The path itself would republish the login, so replace the whole label.
        return "masked-path#" + hashlib.sha256(label.encode()).hexdigest()[:8]
    return label


def collect_text(label: str, raw: bytes, switch: date, index, logins: frozenset[str], salt: str, allow: frozenset[str]) -> list[tuple[str, int, int, str]]:
    if path_before_switch(label, switch):
        return []
    rows = []
    for line, rule, login in scan_text(text_of(raw), index):
        # A reviewed false positive is stored as a salted hash, not as the word.
        if salted(salt, str(rule), login) in allow:
            continue
        rows.append((public_label(label, logins), line, rule, salted(salt, login)[:8]))
    return rows


def scan_range(root: Path, base: str, head: str, switch: date, index, logins, salt, allow) -> list[tuple[str, int, int, str]]:
    if not base:
        raise ScanError("switch config schema")
    names = git_names(root, "diff", "-z", "--name-only", "--diff-filter=ACMRT", base, head)
    rows: list[tuple[str, int, int, str]] = []
    for name in names:
        if path_before_switch(name, switch):
            continue
        try:
            raw = git_bytes(root, "show", f"{head}:{name}")
        except ScanError:
            # Deleted in head: the published tree no longer has the byte.
            continue
        rows.extend(collect_text(name, raw, switch, index, logins, salt, allow))
    listed = git_bytes(root, "rev-list", f"{base}..{head}").decode().split()
    for sha in listed:
        message = git_bytes(root, "show", "-s", "--format=%B", sha)
        label = "commit:" + sha[:12]
        rows.extend(collect_text(label, message, switch, index, logins, salt, allow))
    return rows


def scan_staged(root: Path, switch: date, index, logins, salt, allow) -> list[tuple[str, int, int, str]]:
    names = git_names(root, "diff", "--cached", "-z", "--name-only", "--diff-filter=ACMRT")
    rows: list[tuple[str, int, int, str]] = []
    for name in names:
        if path_before_switch(name, switch):
            continue
        raw = git_bytes(root, "show", f":{name}")
        rows.extend(collect_text(name, raw, switch, index, logins, salt, allow))
    return rows


def scan_dir(directory: Path, switch: date, index, logins, salt, allow) -> list[tuple[str, int, int, str]]:
    if not directory.is_dir():
        raise ScanError("directory unavailable")
    rows: list[tuple[str, int, int, str]] = []
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames:
            path = Path(dirpath) / name
            label = path.relative_to(directory).as_posix()
            if path_before_switch(label, switch):
                continue
            try:
                if path.is_symlink():
                    raw = os.readlink(path).encode()
                elif path.is_file():
                    raw = path.read_bytes()
                else:
                    continue
            except OSError as exc:
                raise ScanError("directory unreadable") from exc
            rows.extend(collect_text(label, raw, switch, index, logins, salt, allow))
    return rows


def scan_message(path: Path, switch: date, index, logins, salt, allow) -> list[tuple[str, int, int, str]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ScanError("message unreadable") from exc
    return collect_text("commit-message", raw, switch, index, logins, salt, allow)


def emit(rows: list[tuple[str, int, int, str]]) -> int:
    for label, line, rule, fingerprint in rows:
        print(f"{label}:{line}: rule {rule} {fingerprint}")
    print(f"person-free new bytes: {len(rows)} findings")
    return 1 if rows else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="person_free_new_bytes.py")
    parser.add_argument("--require-index", action="store_true")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--dir", type=Path)
    parser.add_argument("--message-file", type=Path)
    parser.add_argument("base", nargs="?")
    parser.add_argument("head", nargs="?")
    args = parser.parse_args(argv)
    modes = sum(bool(item) for item in (args.staged, args.dir, args.message_file, args.base))
    if modes > 1 or (args.head and not args.base):
        print("person-free new bytes: choose one of range, --staged, --dir, --message-file")
        return 2
    try:
        root = git_root()
        switch = load_switch(root)
        if switch is None:
            print("person-free new bytes: dormant")
            return 0
        switch_date, configured_base = switch
        raw_index = os.environ.get("EVX_PERSON_INDEX_DIR")
        loaded = load_index(Path(raw_index) if raw_index else None, required=args.require_index)
        if loaded is None:
            print("person-free new bytes: skipped")
            return 0
        salt, logins, allow = loaded
        index = build_handle_index(logins)
        if args.staged:
            rows = scan_staged(root, switch_date, index, logins, salt, allow)
        elif args.dir:
            rows = scan_dir(args.dir, switch_date, index, logins, salt, allow)
        elif args.message_file:
            rows = scan_message(args.message_file, switch_date, index, logins, salt, allow)
        else:
            base = args.base or configured_base or ""
            head = args.head or "HEAD"
            rows = scan_range(root, base, head, switch_date, index, logins, salt, allow)
    except ScanError as exc:
        print(f"person-free new bytes: {exc}")
        return 2
    return emit(rows)


if __name__ == "__main__":
    raise SystemExit(main())
