"""Recall is a measured number at every predicate version, not an assertion.

The fixture was collected independently of the classifier (a live-web agent
seeded with ~725 candidates, each verified against the GitHub API) precisely so
that a later version cannot quietly trade recall away while its authors watch
only the cases they already knew about.

The floor is deliberately below the measured value. It exists to catch a
COLLAPSE, not to freeze a number: a predicate amendment is allowed to move
recall a few points in either direction with its reasons published, and is not
allowed to halve it silently.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))

from ai_scope import classify

FIXTURE = ROOT / "tests" / "fixtures" / "recall-fixture-2026-08.json"
FLOOR = 0.80          # measured 0.891 at the two-tier version, 2026-08-03


def _rows():
    census = ROOT / "data" / "census" / "2026-08"
    raw_path = census / "raw-500plus.jsonl"
    if not raw_path.exists():          # gitignored working data
        return None
    raw = {}
    for line in raw_path.open():
        row = json.loads(line)
        raw[row["full_name"]] = row
    deep = {}
    for path in census.glob("deepcheck*.jsonl"):
        for line in path.open():
            d = json.loads(line)
            deep[d["full_name"]] = d
    return raw, deep


def test_recall_does_not_collapse():
    rows = _rows()
    if rows is None:
        import pytest
        pytest.skip("census working data absent (gitignored); run the census")
    raw, deep = rows
    fixture = json.loads(FIXTURE.read_text())
    seen = hit = 0
    for entry in fixture["entries"]:
        name = entry["full_name"]
        if name not in raw or name not in deep:
            continue
        seen += 1
        row, d = raw[name], deep[name]
        if classify(name.split("/")[-1], row["description"], row["topics"],
                    readme=d.get("readme"), manifests=d.get("manifests")):
            hit += 1
    assert seen > 100, "fixture did not resolve against the census data"
    recall = hit / seen
    assert recall >= FLOOR, (
        f"recall collapsed to {recall:.3f} on {seen} known-true AI systems "
        f"(floor {FLOOR}); a predicate amendment may move this with published "
        f"reasons, it may not halve it silently")
