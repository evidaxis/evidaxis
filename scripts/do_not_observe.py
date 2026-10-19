#!/usr/bin/env python3
"""Numeric repository ids that a run must not observe.

EVX_DO_NOT_OBSERVE is a comma-separated list of repository ids. The value
is a secret. This module answers is_blocked(repo_id) for that list and
offers the same answer on the command line. It does not record the list
and it is not called by the collectors.

    python3 scripts/do_not_observe.py ID [ID ...]

Exit 0 when every id is clear, 1 when any id is blocked, 2 when the list
or an argument is malformed. The secret list itself is never printed.
"""
from __future__ import annotations

import argparse
import os


class ListError(Exception):
    """The environment value is not a list of numeric ids."""


def parse_ids(raw: str | None) -> frozenset[int]:
    if raw is None or raw.strip() == "":
        return frozenset()
    found: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token.isascii() or not token.isdigit():
            raise ListError("malformed list")
        found.add(int(token))
    return frozenset(found)


def load_blocked(raw: str | None = None) -> frozenset[int]:
    if raw is None:
        raw = os.environ.get("EVX_DO_NOT_OBSERVE")
    return parse_ids(raw)


def is_blocked(repo_id: int, blocked: frozenset[int] | None = None) -> bool:
    if isinstance(repo_id, bool) or not isinstance(repo_id, int):
        raise ListError("malformed id")
    ids = load_blocked() if blocked is None else blocked
    return repo_id in ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="do_not_observe.py")
    parser.add_argument("repo_id", nargs="+")
    args = parser.parse_args(argv)
    try:
        blocked = load_blocked()
    except ListError:
        print("do-not-observe: malformed list")
        return 2
    any_blocked = False
    for token in args.repo_id:
        if not token.isascii() or not token.isdigit():
            print("do-not-observe: malformed id")
            return 2
        if is_blocked(int(token), blocked):
            print(f"{token} blocked")
            any_blocked = True
        else:
            print(f"{token} clear")
    return 1 if any_blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
