"""A throwaway key created by governance_sign.py. ssh-keygen checks the signature.

The test skips when ssh-keygen is not installed. Nothing is written under the
real home directory, and no governance/allowed_signers file is created.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "governance_sign.py"


def _require_ssh() -> None:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen is missing")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def _keygen(tmp_path: Path) -> tuple[Path, Path, str]:
    folder = tmp_path / "keys"
    key = folder / "governance_ed25519.pem"
    passphrase = folder / "governance_ed25519.passphrase"
    result = _run("keygen", "--key", str(key), "--passphrase-file", str(passphrase))
    assert result.returncode == 0, result.stdout + result.stderr
    secret = passphrase.read_text(encoding="ascii").strip()
    assert secret not in result.stdout and secret not in result.stderr
    return key, passphrase, result.stdout


def test_key_and_passphrase_files_are_private(tmp_path: Path) -> None:
    key, passphrase, _stdout = _keygen(tmp_path)
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    assert stat.S_IMODE(passphrase.stat().st_mode) == 0o600
    assert stat.S_IMODE(key.parent.stat().st_mode) == 0o700
    assert b"PRIVATE KEY" in key.read_bytes()
    assert b"ENCRYPTED" in key.read_bytes()


def test_signature_verifies_and_one_changed_byte_fails(tmp_path: Path) -> None:
    _require_ssh()
    key, passphrase, stdout = _keygen(tmp_path)
    document = tmp_path / "decision.md"
    document.write_text("adopt\n", encoding="utf-8")
    digest = hashlib.sha256(document.read_bytes()).hexdigest()
    signed = _run(
        "sign", "--file", str(document), "--expect-sha256", digest,
        "--key", str(key), "--passphrase-file", str(passphrase),
    )
    assert signed.returncode == 0, signed.stdout + signed.stderr
    signature = Path(str(document) + ".sig")
    approval = Path(str(document) + ".approval.txt")
    assert signature.is_file()
    approval_text = approval.read_text(encoding="ascii")
    assert f"sha256: {digest}" in approval_text
    assert "utc_date: " in approval_text
    signers = tmp_path / "allowed_signers"
    signers.write_text(stdout.splitlines()[1] + "\n", encoding="ascii")
    # -f below is this throwaway file. The published governance/allowed_signers is not used.

    def verify() -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                "ssh-keygen", "-Y", "verify",
                "-f", str(signers),
                "-I", "governance@evidaxis.org",
                "-n", "evidaxis-governance",
                "-s", str(signature),
            ],
            input=document.read_bytes(),
            capture_output=True,
        )

    assert verify().returncode == 0
    body = bytearray(document.read_bytes())
    body[0] ^= 0x01
    document.write_bytes(body)
    assert verify().returncode != 0


def test_wrong_expect_sha256_is_refused(tmp_path: Path) -> None:
    key, passphrase, _stdout = _keygen(tmp_path)
    document = tmp_path / "decision.md"
    document.write_text("adopt\n", encoding="utf-8")
    digest = hashlib.sha256(document.read_bytes()).hexdigest()
    wrong = ("0" if digest[-1] != "0" else "1") * 64
    refused = _run(
        "sign", "--file", str(document), "--expect-sha256", wrong,
        "--key", str(key), "--passphrase-file", str(passphrase),
    )
    assert refused.returncode != 0
    assert "mismatch" in refused.stdout
    assert not Path(str(document) + ".sig").exists()
    assert not Path(str(document) + ".approval.txt").exists()
    secret = passphrase.read_text(encoding="ascii").strip()
    assert secret not in refused.stdout and secret not in refused.stderr


def test_restore_test_verifies_a_backup_copy(tmp_path: Path) -> None:
    _require_ssh()
    key, passphrase, _stdout = _keygen(tmp_path)
    backup = tmp_path / "backup.pem"
    backup.write_bytes(key.read_bytes())
    os.chmod(backup, 0o600)
    result = _run("restore-test", "--backup", str(backup), "--passphrase-file", str(passphrase))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "restore-test: ok\n"
    secret = passphrase.read_text(encoding="ascii").strip()
    assert secret not in result.stdout and secret not in result.stderr
    assert backup.read_bytes() == key.read_bytes()
