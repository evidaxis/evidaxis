"""snapshot_identity - content-addressed snapshot_id post-step.

etl/collect.py is byte-frozen and mints
    snapshot_id = sha1(METHODOLOGY_VERSION + manifest_hash)[:12]
where manifest_hash covers only the SEED lists (github_repos, openalex_works), not
entity payloads. Two published snapshots can therefore share a snapshot_id while
holding different scores (see data/observations/ERRATA.md, 2026-07-10 collision
f1f2495d518d on 2026-07-03 vs 2026-07-04).

This post-step rewrites snapshot_id to a content hash of the payload:
    sha256(canonical_json(snapshot WITHOUT the snapshot_id field))[:12]
so every published measurement has a unique, content-derived identity going
forward. Published historical snapshots are NOT rewritten (append-only archive);
the known collision is allowlisted for --check via
data/observations/errata_snapshot_id.json.

New code, lives OUTSIDE the frozen etl/. Pure standard library.

Usage:
  python collectors/snapshot_identity.py                  # rewrite today's snapshot_id
  python collectors/snapshot_identity.py --date YYYY-MM-DD
  python collectors/snapshot_identity.py --check          # CI: no unallowlisted collisions
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAPSHOTS = REPO / "data" / "snapshots"
ERRATA = REPO / "data" / "observations" / "errata_snapshot_id.json"


def canonical_payload(snap: dict) -> dict:
    """Snapshot dict without the identity field being computed."""
    return {k: v for k, v in snap.items() if k != "snapshot_id"}


def canonical_json(obj: dict) -> str:
    """Deterministic JSON for content-addressing (sort keys, tight separators, UTF-8)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(snap: dict) -> str:
    """Full sha256 hex of the canonical payload (no snapshot_id)."""
    return hashlib.sha256(canonical_json(canonical_payload(snap)).encode("utf-8")).hexdigest()


def content_snapshot_id(snap: dict) -> str:
    """12-hex content-addressed snapshot_id."""
    return payload_hash(snap)[:12]


# Bundle files that REFERENCE the snapshot_id (they do not define it). They must
# be kept in lockstep with snapshot.json or an auditor sees three identities in
# one sealed bundle (gemini cross-review finding, 2026-07-10).
ID_MIRROR_FILES = ("manifest.json", "provenance.json")


def rewrite_snapshot(path: Path) -> tuple[str, str, bool]:
    """Recompute and write snapshot_id (snapshot.json + bundle mirrors).
    Returns (old_id, new_id, changed)."""
    snap = json.loads(path.read_text(encoding="utf-8"))
    old = snap.get("snapshot_id", "")
    new = content_snapshot_id(snap)
    if old == new:
        return old, new, False
    snap["snapshot_id"] = new
    # Preserve load order / 2-space indent used by the collector.
    path.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name in ID_MIRROR_FILES:
        mirror = path.parent / name
        if not mirror.is_file():
            continue
        doc = json.loads(mirror.read_text(encoding="utf-8"))
        if doc.get("snapshot_id") == new:
            continue
        doc["snapshot_id"] = new
        mirror.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return old, new, True


def _load_errata() -> list[dict]:
    if not ERRATA.is_file():
        return []
    data = json.loads(ERRATA.read_text(encoding="utf-8"))
    return list(data.get("allowlist") or [])


def _allowlisted_pair(sid: str, date_a: str, hash_a: str, date_b: str, hash_b: str,
                      allowlist: list[dict]) -> bool:
    """True if (date_a,hash_a) and (date_b,hash_b) match an erratum entry for sid."""
    for entry in allowlist:
        if entry.get("snapshot_id") != sid:
            continue
        hashes = entry.get("payload_hashes") or {}
        # Entry must cover both dates with the EXACT on-disk hash per date; a
        # swapped-hash erratum is a wrong erratum, not a pass (review 2026-07-10).
        if not {date_a, date_b} <= set(hashes.keys()):
            continue
        if hashes.get(date_a) == hash_a and hashes.get(date_b) == hash_b:
            return True
    return False


def check_collisions() -> int:
    """Exit 1 if any two snapshot dirs share snapshot_id with different payload hashes
    unless the pair is listed in errata_snapshot_id.json with matching hashes."""
    if not SNAPSHOTS.is_dir():
        print("snapshot_identity --check: no data/snapshots/ directory")
        return 0

    by_id: dict[str, list[tuple[str, str, int]]] = {}  # sid -> [(date, full_hash, n_entities)]
    for d in sorted(p for p in SNAPSHOTS.iterdir() if p.is_dir()):
        path = d / "snapshot.json"
        if not path.is_file():
            continue
        snap = json.loads(path.read_text(encoding="utf-8"))
        sid = snap.get("snapshot_id")
        if not sid:
            print(f"snapshot_identity --check: {d.name} missing snapshot_id")
            return 1
        # Intra-bundle consistency: manifest/provenance must reference the same id.
        for name in ID_MIRROR_FILES:
            mirror = d / name
            if not mirror.is_file():
                continue
            mid = json.loads(mirror.read_text(encoding="utf-8")).get("snapshot_id")
            if mid is not None and mid != sid:
                print(
                    f"snapshot_identity --check: FAILED — {d.name}/{name} snapshot_id "
                    f"{mid} != snapshot.json {sid} (bundle identity divergence)"
                )
                return 1
        ph = payload_hash(snap)
        n = len(snap.get("entities") or [])
        by_id.setdefault(sid, []).append((d.name, ph, n))

    allowlist = _load_errata()
    bad: list[str] = []
    allowed_notes: list[str] = []

    for sid, rows in sorted(by_id.items()):
        if len(rows) < 2:
            continue
        # Group by payload hash: same id + same payload is fine (byte-identical copies).
        by_hash: dict[str, list[str]] = {}
        for date, ph, _n in rows:
            by_hash.setdefault(ph, []).append(date)
        if len(by_hash) < 2:
            continue
        # Distinct payloads under one snapshot_id — collision unless allowlisted.
        dates_hashes = [(date, ph) for date, ph, _n in rows]
        # Check every pair of distinct hashes.
        items = list(by_hash.items())  # (hash, [dates...])
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                h_a, dates_a = items[i]
                h_b, dates_b = items[j]
                # Any date from group A vs any date from group B must be allowlisted.
                ok = True
                for da in dates_a:
                    for db in dates_b:
                        if not _allowlisted_pair(sid, da, h_a, db, h_b, allowlist):
                            ok = False
                            bad.append(
                                f"  {sid}: {da} (hash {h_a[:12]}…) vs {db} (hash {h_b[:12]}…) "
                                f"— not allowlisted"
                            )
                if ok:
                    for da in dates_a:
                        for db in dates_b:
                            allowed_notes.append(
                                f"  {sid}: {da} vs {db} (allowlisted collision)"
                            )

    for note in allowed_notes:
        print(f"snapshot_identity --check: known erratum{note}")
    if bad:
        print("snapshot_identity --check: FAILED — unallowlisted snapshot_id collisions:")
        for line in bad:
            print(line)
        try:
            errata_disp = ERRATA.relative_to(REPO)
        except ValueError:
            errata_disp = ERRATA
        print(f"(errata file: {errata_disp})")
        return 1
    print(
        f"snapshot_identity --check: ok "
        f"({sum(len(v) for v in by_id.values())} snapshots, "
        f"{len(allowed_notes)} allowlisted collision pair(s))"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Content-addressed snapshot_id rewrite / collision check."
    )
    ap.add_argument(
        "--date",
        default=None,
        help="snapshot date YYYY-MM-DD (default: today UTC)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="CI mode: fail on unallowlisted snapshot_id collisions",
    )
    args = ap.parse_args()

    if args.check:
        return check_collisions()

    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = SNAPSHOTS / date / "snapshot.json"
    if not path.is_file():
        print(f"snapshot_identity: no snapshot at {path.relative_to(REPO)}")
        return 1
    old, new, changed = rewrite_snapshot(path)
    if changed:
        print(f"snapshot_identity: {date} snapshot_id {old} -> {new}")
    else:
        print(f"snapshot_identity: {date} snapshot_id already content-addressed ({new}) (no-op)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
