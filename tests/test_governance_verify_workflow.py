"""governance-verify.yml is outside the release chain.

With no allowed_signers file and no signature files the job passes.
A signature file without allowed_signers fails.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "governance-verify.yml"
SIGN = REPO / "scripts" / "governance_sign.py"
PIN = "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _script() -> str:
    steps = _workflow()["jobs"]["verify"]["steps"]
    return steps[-1]["run"]


def test_checkout_is_pinned_and_the_trigger_names_signatures() -> None:
    workflow = _workflow()
    checkout = workflow["jobs"]["verify"]["steps"][0]["uses"]
    assert checkout.startswith(PIN)
    triggers = workflow[True]  # PyYAML reads the Actions key "on" as True.
    paths = triggers["push"]["paths"]
    assert "governance/**.sig" in paths
    script = _script()
    assert "ssh-keygen -Y verify -f governance/allowed_signers -I governance@evidaxis.org -n evidaxis-governance" in script
    assert "weekly-snapshot" not in WORKFLOW.read_text(encoding="utf-8")


def test_job_passes_with_no_signers_and_no_signatures(tmp_path: Path) -> None:
    result = subprocess.run(["bash", "-c", _script()], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "no signatures" in result.stdout


def test_job_rejects_a_signature_without_signers(tmp_path: Path) -> None:
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "note.md").write_text("adopt\n", encoding="utf-8")
    (governance / "note.md.sig").write_text("not a signature\n", encoding="utf-8")
    result = subprocess.run(["bash", "-c", _script()], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0
    assert "allowed_signers missing" in result.stdout


def test_job_verifies_a_good_signature_and_rejects_a_changed_byte(tmp_path: Path) -> None:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen is missing")
    folder = tmp_path / "keys"
    key = folder / "key.pem"
    passphrase = folder / "pass"
    generated = subprocess.run(
        [sys.executable, str(SIGN), "keygen", "--key", str(key), "--passphrase-file", str(passphrase)],
        capture_output=True, text=True, check=True,
    )
    governance = tmp_path / "governance"
    governance.mkdir()
    document = governance / "note.md"
    document.write_text("adopt\n", encoding="utf-8")
    digest = hashlib.sha256(document.read_bytes()).hexdigest()
    subprocess.run(
        [sys.executable, str(SIGN), "sign", "--file", str(document), "--expect-sha256", digest,
         "--key", str(key), "--passphrase-file", str(passphrase)],
        check=True, capture_output=True, text=True,
    )
    (governance / "allowed_signers").write_text(generated.stdout.splitlines()[1] + "\n", encoding="ascii")
    good = subprocess.run(["bash", "-c", _script()], cwd=tmp_path, capture_output=True, text=True)
    assert good.returncode == 0, good.stderr
    body = bytearray(document.read_bytes())
    body[0] ^= 0x01
    document.write_bytes(body)
    rejected = subprocess.run(["bash", "-c", _script()], cwd=tmp_path, capture_output=True, text=True)
    assert rejected.returncode != 0
