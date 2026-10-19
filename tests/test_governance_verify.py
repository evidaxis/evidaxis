"""A throwaway ed25519 key signs one file. The repo's allowed_signers stays absent.

ssh-keygen is optional on a machine that does not have it: the test skips.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "governance_verify.py"
IDENTITY = "evx-test-signer"


def test_throwaway_key_verifies_and_a_tampered_file_does_not(tmp_path: Path) -> None:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen is missing")
    key = tmp_path / "key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-f", str(key), "-N", "", "-C", IDENTITY],
        check=True, capture_output=True,
    )
    document = tmp_path / "decision.md"
    document.write_text("adopt\n", encoding="utf-8")
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "evidaxis-governance", str(document)],
        check=True, capture_output=True,
    )
    public = key.with_suffix(".pub").read_text(encoding="utf-8").split()
    signers = tmp_path / "allowed_signers"
    signers.write_text(
        f'{IDENTITY} namespaces="evidaxis-governance" {public[0]} {public[1]}\n',
        encoding="utf-8",
    )
    assert not (REPO / "governance" / "allowed_signers").exists()

    def verify() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "-I", IDENTITY, "-f", str(signers), str(document)],
            capture_output=True, text=True,
        )

    good = verify()
    assert good.returncode == 0
    assert good.stdout == "governance signature: ok\n"

    document.write_text("changed\n", encoding="utf-8")
    rejected = verify()
    assert rejected.returncode == 1
    assert rejected.stdout == "governance signature: rejected\n"
    assert not (REPO / "governance" / "allowed_signers").exists()
