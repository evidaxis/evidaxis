"""Every seeds vertical must resolve through the taxonomy, and carry a label.

Found live on 2026-08-03: the first census activation added the vertical
`unassigned-v1` to etl/seeds.json, and `taxonomy_v2.resolve()` raises KeyError
on an unknown cohort key by design. Nothing connected the two, so the weekly
snapshot - which runs unattended on Saturdays - would have died on its next run
and taken the whole observation chain with it. Fail-closed is correct; being
invisible until Saturday is not.

The chain has three links and all three must hold, because breaking any one of
them fails a different job at a different hour:
  seeds vertical  ->  taxonomy_v2.VKEY_TO_V2   (weekly snapshot, Python)
  cohort slug     ->  taxonomy/nodes-v2.json   (remap_snapshot, Python)
  cohort slug     ->  web/src/lib/cohorts.ts   (site build, TypeScript)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))

from taxonomy_v2 import resolve

SEEDS = json.loads((ROOT / "etl" / "seeds.json").read_text())
NODES = json.loads((ROOT / "taxonomy" / "nodes-v2.json").read_text())
COHORT_LABELS = {n["slug"]: n["name"]
                 for n in NODES["nodes"] if n.get("level") == "cohort"}
COHORTS_TS = (ROOT / "web" / "src" / "lib" / "cohorts.ts").read_text()


def test_every_seeds_vertical_resolves():
    for vkey in SEEDS["verticals"]:
        field, cohort = resolve(vkey)          # raises if unmapped
        assert field and cohort


def test_every_resolved_cohort_has_a_canonical_label():
    for vkey in SEEDS["verticals"]:
        _, cohort = resolve(vkey)
        assert cohort in COHORT_LABELS, (
            f"cohort {cohort!r} (from seeds vertical {vkey!r}) has no node in "
            f"taxonomy/nodes-v2.json; remap_snapshot raises on it")


def test_every_resolved_cohort_is_known_to_the_site():
    for vkey in SEEDS["verticals"]:
        _, cohort = resolve(vkey)
        assert cohort in COHORTS_TS, (
            f"cohort {cohort!r} is absent from web/src/lib/cohorts.ts; the site "
            f"would fall back to a truncated label for every card in it")
