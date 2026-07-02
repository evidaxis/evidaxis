"""taxonomy_v2 mapping: v1 vertical key -> v2 (field, cohort), idempotency, unknown-key guard."""
import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
from taxonomy_v2 import remap_snapshot, resolve


def test_resolve_v1_key():
    assert resolve("ai-coding-agents") == ("ai-agents", "coding-agents")
    assert resolve("diffusion-media-gen") == ("multimodal-media", "media-generation")


def test_resolve_is_idempotent_on_v2_slug():
    # an already-migrated cohort slug resolves to itself with its field
    assert resolve("coding-agents") == ("ai-agents", "coding-agents")
    assert resolve("media-generation") == ("multimodal-media", "media-generation")


def test_resolve_unknown_raises():
    with pytest.raises(KeyError):
        resolve("totally-unknown-cohort")


def test_remap_v1_entity():
    snap = {"entities": [{"entity_id": "e_X", "cohort": "ai-coding-agents", "industry": "developer-tools", "sub_niche": "coding-agents"}]}
    remap_snapshot(snap)
    e = snap["entities"][0]
    assert (e["industry"], e["sub_niche"], e["cohort"]) == ("ai-agents", "coding-agents", "coding-agents")
    assert snap["cohorts"]["coding-agents"]["industry"] == "ai-agents"
    assert snap["cohorts"]["coding-agents"]["label"]  # non-empty label from nodes-v2


def test_remap_idempotent_on_live_snapshot():
    # remapping the current live v2 snapshot must NOT change any taxonomy field
    date = json.loads((REPO / "data/latest.json").read_text())["snapshot_date"]
    snap = json.loads((REPO / "data/snapshots" / date / "snapshot.json").read_text())
    before = [(e["entity_id"], e["industry"], e["sub_niche"], e["cohort"]) for e in snap["entities"]]
    before_cohorts = copy.deepcopy(snap["cohorts"])
    remap_snapshot(snap)
    after = [(e["entity_id"], e["industry"], e["sub_niche"], e["cohort"]) for e in snap["entities"]]
    assert before == after, "remap changed a live v2 taxonomy field (map drifted from live)"
    assert before_cohorts == snap["cohorts"], "remap changed live cohorts dict"
