"""Drift guard for the immutable genesis deposit.

The Zenodo genesis DOI froze genesis-deposit/code/* at methodology m1. Those DEPOSITED
copies are immutable and must never change. The live etl/ copies may EVOLVE post-genesis
(e.g. the D10a gate fix -> m2), but only with a conscious METHODOLOGY_VERSION bump, never
a silent drift. So:

  * archive_pin.py is unchanged since genesis -> must still match its frozen deposit byte-for-byte.
  * collect.py has consciously advanced to m2 -> it MAY differ from the frozen m1 deposit, but
    ONLY if its METHODOLOGY_VERSION has bumped past the deposit's (m1). The frozen deposit copy
    must itself remain m1 (editing the immutable genesis artifact is forbidden).

Keeping this honest is the signal that the live code never drifts from what the DOI certifies
without a deliberate, re-depositable version change.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _methodology_version(p: Path):
    m = re.search(r'METHODOLOGY_VERSION\s*=\s*"([^"]+)"', p.read_text())
    return m.group(1) if m else None


def test_archive_pin_unchanged_matches_frozen_deposit():
    live = REPO / "etl/archive_pin.py"
    dep = REPO / "genesis-deposit/code/archive_pin.py"
    assert live.exists() and dep.exists()
    assert _sha(live) == _sha(dep), (
        "archive_pin.py drifted from the frozen genesis deposit (it has not consciously "
        "versioned). Re-deposit under a new versioned DOI or revert."
    )


def test_collect_deposit_frozen_and_live_consciously_versioned():
    live = REPO / "etl/collect.py"
    dep = REPO / "genesis-deposit/code/collect.py"
    assert live.exists() and dep.exists()
    # the immutable genesis deposit must stay m1
    assert _methodology_version(dep) == "m1", (
        "the genesis deposit code must stay frozen at methodology m1 (immutable DOI artifact)"
    )
    if _sha(live) != _sha(dep):
        # live evolved -> a conscious METHODOLOGY_VERSION bump is mandatory (no silent drift)
        live_ver = _methodology_version(live)
        assert live_ver and live_ver != "m1", (
            "etl/collect.py drifted from the frozen m1 genesis deposit WITHOUT a "
            "METHODOLOGY_VERSION bump. Either revert, or bump the version (a conscious, "
            "re-depositable change)."
        )
