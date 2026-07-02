"""taxonomy_v2 - map a fresh collect.py snapshot (tax_1) onto the locked taxonomy v2.

collect.py is byte-frozen (genesis DOI) and emits the v1 taxonomy: each entity gets
industry=seeds industry_slug, sub_niche=seeds subniche_slug, cohort=vertical-key, and
a tax_1 taxonomy/nodes.json (domain -> industry -> sub_niche). The live site is
taxonomy v2 (domain -> field -> cohort, cohort-canonical URLs), produced once by an
ad-hoc migration. This post-step makes that migration REPEATABLE and deterministic so
the weekly heartbeat and any universe expansion produce consistent v2 data WITHOUT
editing frozen collect.py.

It (a) remaps each snapshot entity's industry/sub_niche/cohort and rebuilds
snapshot.cohorts via a LOCKED vkey->(field,cohort) map (derived 1:1 from the live v2
snapshot, verified idempotent), and (b) restores the canonical v2 taxonomy from
taxonomy/nodes-v2.json (which collect.py never writes, so it survives a collect run).

New code, outside frozen etl/. Pure standard library.

Usage:
  python collectors/taxonomy_v2.py [--date YYYY-MM-DD]   # remap that snapshot (default: latest.json)
  python collectors/taxonomy_v2.py --verify              # assert idempotent on the current snapshot
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
CANON_NODES = REPO / "taxonomy" / "nodes-v2.json"
ACTIVE_NODES = REPO / "taxonomy" / "nodes.json"

# LOCKED map. collect.py sets entity.cohort = the seeds vertical key (v1). This maps
# each v1 vertical key -> the v2 (field slug, cohort slug). Derived 1:1 from the live
# v2 snapshot (migration commit ec70ecc). APPEND-ONLY: never remap an existing key to a
# different cohort (that would silently re-slug a system; taxonomy-v2-LOCKED rule 1).
VKEY_TO_V2 = {
    "robotics-embodied":     ("robotics-embodied", "robotics-embodied"),
    "ai-drug-discovery":     ("ai-for-science", "ai-drug-discovery"),
    "ai-coding-agents":      ("ai-agents", "coding-agents"),
    "llm-inference-serving": ("ai-infrastructure", "inference-serving"),
    "agent-frameworks":      ("ai-agents", "agent-frameworks"),
    "post-training-rl":      ("foundation-models", "post-training-alignment"),
    "diffusion-media-gen":   ("multimodal-media", "media-generation"),
    "multimodal-vlm":        ("foundation-models", "multimodal-foundation-models"),
}
# v2 cohort slug -> its field, so an already-migrated snapshot resolves to itself (idempotent).
V2_COHORT_TO_FIELD = {cohort: field for field, cohort in VKEY_TO_V2.values()}


def resolve(cohort_key: str) -> tuple:
    """(field, cohort) for a v1 vertical key OR an already-v2 cohort slug. Raises on unknown."""
    if cohort_key in VKEY_TO_V2:
        return VKEY_TO_V2[cohort_key]
    if cohort_key in V2_COHORT_TO_FIELD:
        return (V2_COHORT_TO_FIELD[cohort_key], cohort_key)
    raise KeyError(f"unknown cohort key {cohort_key!r}: add it to VKEY_TO_V2 before ingesting")


def _cohort_labels() -> dict:
    canon = json.loads(CANON_NODES.read_text())
    return {n["slug"]: n["name"] for n in canon["nodes"] if n.get("level") == "cohort"}


def remap_snapshot(snap: dict) -> dict:
    """Remap entities' industry/sub_niche/cohort to v2 and rebuild snapshot.cohorts. In place."""
    labels = _cohort_labels()
    cohorts = {}
    for e in snap["entities"]:
        field, cohort = resolve(e["cohort"])
        e["industry"], e["sub_niche"], e["cohort"] = field, cohort, cohort
        if cohort not in cohorts:
            if cohort not in labels:
                raise KeyError(f"cohort {cohort!r} has no label in nodes-v2.json")
            cohorts[cohort] = {"label": labels[cohort], "industry": field, "sub_niche": cohort}
    snap["cohorts"] = cohorts
    return snap


def _snapshot_path(date: str | None) -> Path:
    if date is None:
        date = json.loads((DATA / "latest.json").read_text())["snapshot_date"]
    return DATA / "snapshots" / date / "snapshot.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Map a collect.py snapshot onto taxonomy v2.")
    ap.add_argument("--date", default=None, help="snapshot date (default: latest.json)")
    ap.add_argument("--verify", action="store_true", help="assert idempotent; do not write")
    args = ap.parse_args()

    path = _snapshot_path(args.date)
    snap = json.loads(path.read_text())

    if args.verify:
        before = json.dumps([(e["entity_id"], e["industry"], e["sub_niche"], e["cohort"]) for e in snap["entities"]], sort_keys=True)
        before_cohorts = json.dumps(snap.get("cohorts", {}), sort_keys=True)
        remap_snapshot(snap)
        after = json.dumps([(e["entity_id"], e["industry"], e["sub_niche"], e["cohort"]) for e in snap["entities"]], sort_keys=True)
        after_cohorts = json.dumps(snap["cohorts"], sort_keys=True)
        ok = (before == after) and (before_cohorts == after_cohorts) and (ACTIVE_NODES.read_text() == CANON_NODES.read_text())
        print(f"taxonomy_v2 --verify: {'IDEMPOTENT (snapshot already v2)' if ok else 'DRIFT vs v2 canonical'}")
        return 0 if ok else 1

    remap_snapshot(snap)
    path.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n")
    shutil.copyfile(CANON_NODES, ACTIVE_NODES)  # restore v2 taxonomy (collect.py clobbers it to tax_1)
    n_cohorts = len(snap["cohorts"])
    print(f"taxonomy_v2: {path.relative_to(REPO)} remapped to v2 ({len(snap['entities'])} entities, {n_cohorts} cohorts); nodes.json restored to tax_2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
