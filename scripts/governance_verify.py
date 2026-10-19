#!/usr/bin/env python3
"""Verify a detached governance signature with the public allowed signers.

The namespace is fixed. A caller cannot point the check at another namespace.
The signers file is written by the steward with the block-zero key; this
script does not create it.

    ssh-keygen -Y verify -f governance/allowed_signers -I <identity> \\
        -n evidaxis-governance -s <file>.sig < <file>

    python3 scripts/governance_verify.py -I <identity> [-f signers] <file>
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

NAMESPACE = "evidaxis-governance"


def default_signers(document: Path) -> Path:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=document.parent if document.parent.is_dir() else None,
            capture_output=True,
            check=False,
        )
    except OSError:
        proc = None
    if proc is not None and proc.returncode == 0 and proc.stdout.strip():
        root = Path(os.fsdecode(proc.stdout.strip()))
    else:
        root = Path(__file__).resolve().parent.parent
    return root / "governance" / "allowed_signers"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="governance_verify.py")
    parser.add_argument("document", type=Path)
    parser.add_argument("-I", "--identity", required=True)
    parser.add_argument("-f", "--signers", type=Path)
    parser.add_argument("-s", "--signature", type=Path)
    args = parser.parse_args(argv)
    signers = args.signers or default_signers(args.document)
    signature = args.signature or Path(str(args.document) + ".sig")
    if not args.document.is_file() or not signers.is_file() or not signature.is_file():
        print("governance signature: missing file")
        return 2
    if shutil.which("ssh-keygen") is None:
        print("governance signature: ssh-keygen missing")
        return 2
    try:
        payload = args.document.read_bytes()
    except OSError:
        print("governance signature: missing file")
        return 2
    try:
        proc = subprocess.run(
            [
                "ssh-keygen", "-Y", "verify",
                "-f", str(signers),
                "-I", args.identity,
                "-n", NAMESPACE,
                "-s", str(signature),
            ],
            input=payload,
            capture_output=True,
            check=False,
        )
    except OSError:
        print("governance signature: ssh-keygen missing")
        return 2
    if proc.returncode == 0:
        print("governance signature: ok")
        return 0
    # ssh-keygen's own text can quote the file. Keep it off the log.
    print("governance signature: rejected")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
