"""Committed-archive integrity (renewal CP-6) — the local mirror of
.github/workflows/archive-integrity.yml.

Unlike the pipeline tests (which validate freshly-generated tmp artifacts),
these assert the PUBLISHED tree: every committed snapshot verifies against its
own SHA256SUMS, the taxonomy-v2 remap is idempotent on the committed snapshot,
and the genesis snapshot stays byte-identical to the immutable deposit copy.
This is the check that would have caught the 2026-07-01 SHA256SUMS defect
(post-steps mutated the bundle after sums were written; see that folder's
ERRATA.md) before it shipped.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

from refresh_sums import BUNDLE, _sums_text

GENESIS_DATE = "2026-06-27"
GENESIS_FILES = ("SHA256SUMS", "snapshot.json", "manifest.json",
                 "provenance.json", "archive-pointers.json")


def _snapshot_dirs():
    root = REPO / "data" / "snapshots"
    return sorted(p for p in root.iterdir() if p.is_dir())


def test_every_committed_snapshot_matches_its_sums():
    dirs = _snapshot_dirs()
    assert dirs, "no committed snapshots found"
    for snap_dir in dirs:
        sums = snap_dir / "SHA256SUMS"
        assert sums.exists(), f"{snap_dir.name}: SHA256SUMS missing"
        assert sums.read_text() == _sums_text(snap_dir), (
            f"{snap_dir.name}: SHA256SUMS does not match actual bytes "
            f"(a post-step mutated the bundle after sums were written?)"
        )


def test_refresh_sums_verify_cli_is_green():
    """The exact command CI runs must pass against the committed tree."""
    proc = subprocess.run(
        [sys.executable, "collectors/refresh_sums.py", "--verify"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_taxonomy_v2_idempotent_on_committed_snapshot():
    proc = subprocess.run(
        [sys.executable, "collectors/taxonomy_v2.py", "--verify"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_genesis_snapshot_byte_identical_to_deposit():
    for fn in GENESIS_FILES:
        live = REPO / "data" / "snapshots" / GENESIS_DATE / fn
        frozen = REPO / "genesis-deposit" / "data" / fn
        assert frozen.exists(), f"genesis-deposit/data/{fn} missing"
        assert live.exists(), f"live genesis {fn} missing"
        assert live.read_bytes() == frozen.read_bytes(), (
            f"{fn}: live genesis snapshot drifted from the immutable deposit "
            f"(I5 escalation trigger — historical bytes must never change)"
        )


def test_bundle_order_matches_frozen_collector():
    """refresh_sums must keep collect.py's exact file order, or rewritten
    SHA256SUMS would differ byte-wise from collector-written ones."""
    assert BUNDLE == ("snapshot.json", "manifest.json", "provenance.json")
