"""Drift guard for the immutable genesis deposit (audit finding: byte-copied code,
no drift guard). The Zenodo genesis DOI freezes code/collect.py + code/archive_pin.py.
The repo keeps the live copies under etl/. They MUST stay byte-identical to the
deposited copies, or the published artifact no longer matches the running code.

If you intentionally evolve etl/collect.py after the genesis mint, this test should
be updated to compare against a NEW deposit revision (and a new versioned DOI), never
silently relaxed. Keeping it red is the signal that the live code diverged from what
the DOI certifies.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PAIRS = [
    ("etl/collect.py", "genesis-deposit/code/collect.py"),
    ("etl/archive_pin.py", "genesis-deposit/code/archive_pin.py"),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("live_rel,deposit_rel", PAIRS)
def test_deposit_code_matches_live(live_rel, deposit_rel):
    live, deposit = REPO / live_rel, REPO / deposit_rel
    assert live.exists(), f"missing live source {live_rel}"
    assert deposit.exists(), f"missing deposited copy {deposit_rel}"
    assert _sha(live) == _sha(deposit), (
        f"DRIFT: {live_rel} != {deposit_rel}. The genesis DOI freezes the deposited "
        f"copy; the live code changed. Re-deposit under a new versioned DOI or revert."
    )
