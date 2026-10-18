#!/usr/bin/env python3
"""Check tracked text for private, case-insensitive ERE owner patterns.

Patterns stay outside the repository. Diagnostics contain only locations and
pattern numbers, so a CI finding does not republish the private identifier.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


EXCLUDED = ("data/", "etl/", "entities/", "web/.foundation-check/fixtures/")


def main() -> int:
    try:
        pattern_file = os.environ.get("EVX_OWNER_PATTERNS_FILE")
        source = (Path(pattern_file).expanduser().read_text(encoding="utf-8")
                  if pattern_file else os.environ.get("EVX_OWNER_PATTERNS", ""))
    except (OSError, UnicodeError):
        print("owner-trace check failed: cannot read patterns")
        return 2
    patterns = [(n, line) for n, line in enumerate(source.splitlines(), 1) if line.strip()]
    if not patterns:
        print("owner-trace check skipped: no patterns")
        return 0

    try:
        repo = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, check=True).stdout.decode().strip()
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=repo,
                                 capture_output=True, check=True).stdout
        paths = [os.fsdecode(p) for p in tracked.split(b"\0") if p]
        paths = [p for p in paths if not p.startswith(EXCLUDED)
                 and ((Path(repo) / p).is_symlink() or (Path(repo) / p).is_file())]
        links = {p for p in paths if (Path(repo) / p).is_symlink()}
        # Git publishes a symlink's target text, so names and targets are both checked
        # here; contents are read below only for regular files, never through a link.
        records = [os.fsencode(p) for p in paths] + [os.fsencode(os.readlink(Path(repo) / p))
                                                      for p in sorted(links)]
        owners = paths + sorted(links)
        findings = 0
        # A path can carry an identifier too: report such files by index only,
        # both as their own finding and wherever their content matches.
        hidden = {}
        # NUL-separated records keep one record per path, even for names with newlines.
        listing = b"\0".join(records)
        for number, pattern in patterns:
            result = subprocess.run(["grep", "-z", "-n", "-i", "-E", "-e", pattern],
                                    input=listing, capture_output=True)
            if result.returncode not in (0, 1):
                print(f"owner-trace check failed: pattern {number} or file scan error")
                return 2
            for row in filter(None, result.stdout.split(b"\0")):
                record = int(row.partition(b":")[0])
                index = paths.index(owners[record - 1]) + 1
                where = "path" if record <= len(paths) else "link target"
                if (index, where) not in hidden:
                    hidden[(index, where)] = number
                    print(f"tracked file #{index}: owner trace in its {where} (pattern {number})")
                    findings += 1
        names = {paths[index - 1]: f"tracked file #{index}" for index, _ in hidden}
        files = [f"./{p}" for p in paths if p not in links]
        for number, pattern in patterns:
            # grep implements ERE (including POSIX classes); -I omits binary files.
            # Capture its output and errors: neither may expose private text in CI.
            result = subprocess.run(["grep", "-n", "-H", "--null", "-I", "-i", "-E",
                                     "-e", pattern, "--", *files], cwd=repo,
                                    input=b"", capture_output=True)
            if result.returncode not in (0, 1):
                print(f"owner-trace check failed: pattern {number} or file scan error")
                return 2
            remaining = result.stdout
            while remaining:
                path, _, remaining = remaining.partition(b"\0")
                match, _, remaining = remaining.partition(b"\n")
                line = int(match.partition(b":")[0])
                name = os.fsdecode(path).removeprefix("./")
                shown = names.get(name, name)
                print(f"{shown}:{line}: owner trace (pattern {number})")
                findings += 1
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("owner-trace check failed: tracked-file scan unavailable")
        return 2
    print(f"owner-trace check: {findings} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
