"""etl/*.py is frozen. These hashes are the bytes on 2026-10-19."""
from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PINNED = {
    "archive_pin.py": "1b183e35761602cca461c6317469f0497872e8ed26323817cb1b060d027b9881",
    "collect.py": "160a6e1c836aa99a459624ec26a8af2d338d4789dbeec7ff8bc31640a562cd9f",
    "indexnow.py": "b0a89c90036c8aa505a0aa1a525900128ac9412c287c9000343a150ee2d13c1f",
    "reclass_pre_spine.py": "70110fddfaab3affc35d7ff30cfbb54028b60fa76b427962e1a1a64d42f971bf",
}


def test_etl_python_files_match_pinned_sha256() -> None:
    found = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (REPO / "etl").glob("*.py")
        if path.is_file()
    }
    assert found == PINNED
