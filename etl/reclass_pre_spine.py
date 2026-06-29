#!/usr/bin/env python3
"""
PRE_INGEST_CONTRACT §1.2 / §10 — re-class the v2 (pre-spine) baseline as PROVISIONAL.

The live v2 collector wrote a baseline (snapshot 90e607b982fa, methodology m1, collect/2.0)
BEFORE the irreversible spine primitives existed. Per the HALT clause it is kept (append-only,
never deleted) but must be re-classed `provisional:true, spine_complete:false` and excluded from
the foresight back-test denominator and any "first-on-signal" custody claim. The genesis t=0 is
the FIRST snapshot the v3 collector emits AFTER the proving-run-gate is GREEN.

This migration is ADDITIVE (adds two flags; never rewrites existing values) and IDEMPOTENT.
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
FLAGS = {"provisional": True, "spine_complete": False}


def is_pre_spine(obj: dict) -> bool:
    fv = str(obj.get("fetcher_version", ""))
    mv = str(obj.get("methodology_version", ""))
    return fv.startswith("collect/2") or mv == "m1" or obj.get("snapshot_id") == "90e607b982fa"


def patch_json(path: Path) -> bool:
    obj = json.loads(path.read_text())
    if not isinstance(obj, dict) or not is_pre_spine(obj):
        return False
    if obj.get("provisional") is True and obj.get("spine_complete") is False:
        return False
    obj.update(FLAGS)
    path.write_text(json.dumps(obj, indent=2) + "\n")
    return True


def patch_jsonl(path: Path) -> int:
    out, changed = [], 0
    for line in path.read_text().splitlines():
        if not line.strip():
            out.append(line)
            continue
        obj = json.loads(line)
        if is_pre_spine(obj) and not (obj.get("provisional") is True and obj.get("spine_complete") is False):
            obj.update(FLAGS)
            changed += 1
        out.append(json.dumps(obj, separators=(", ", ": ")))
    if changed:
        path.write_text("\n".join(out) + "\n")
    return changed


def main():
    touched = 0
    for p in sorted(DATA.glob("snapshots/*/*.json")):
        if patch_json(p):
            print(f"  flagged {p.relative_to(REPO)}")
            touched += 1
    lp = DATA / "latest.json"
    if lp.exists() and patch_json(lp):
        print(f"  flagged {lp.relative_to(REPO)}")
        touched += 1
    for p in sorted(DATA.glob("history/*.jsonl")):
        n = patch_jsonl(p)
        if n:
            print(f"  flagged {n} record(s) in {p.relative_to(REPO)}")
            touched += 1
    print(f"PRE-SPINE re-class: {touched} artifact(s) flagged provisional (idempotent).")


if __name__ == "__main__":
    main()
