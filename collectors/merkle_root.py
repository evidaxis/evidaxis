"""merkle_root - content-addressed integrity root over the whole data/ archive.

A deterministic binary Merkle tree over every file under data/ (excluding
data/integrity/, which holds these very artifacts and must not hash itself).
The root anchors the archive: flipping a single byte anywhere in data/ changes
the root, so a stamped root is a compact, un-forgeable witness that the archive
existed exactly as-is at time T. Combined with the weekly OpenTimestamps stamp,
this is proof-of-priority for the entire corpus, not just one snapshot file.

Leaves and internal nodes are domain-separated (0x00 / 0x01) so no leaf can be
passed off as an internal node (second-preimage hardening). Leaves bind the file
PATH to its content, so a rename or reorder is detected, not just a content edit.

New code, lives OUTSIDE the frozen etl/. Pure standard library.

Usage:
  python collectors/merkle_root.py            # write data/integrity/archive-root-<date>.json
  python collectors/merkle_root.py --verify   # recompute, compare to latest recorded root (exit 1 on mismatch)
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
INTEGRITY = DATA / "integrity"

_LEAF = b"\x00"
_NODE = b"\x01"


def leaf(rel_path: str, content: bytes) -> bytes:
    """Domain-separated leaf digest binding a file's repo-relative path to its bytes."""
    return hashlib.sha256(_LEAF + rel_path.encode("utf-8") + b"\x00" + content).digest()


def merkle_root(leaves: list) -> bytes:
    """Fold a list of leaf digests into a single root digest.

    Pairwise sha256(0x01 || left || right); an odd node at a level is promoted
    unchanged. Empty input yields sha256(b"") so the function is always total.
    """
    if not leaves:
        return hashlib.sha256(b"").digest()
    level = list(leaves)
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                nxt.append(hashlib.sha256(_NODE + level[i] + level[i + 1]).digest())
            else:
                nxt.append(level[i])  # odd one out is promoted unchanged
        level = nxt
    return level[0]


def _archive_files() -> list:
    """All files under data/, in a deterministic order, excluding data/integrity/."""
    return [
        p for p in sorted(DATA.rglob("*"))
        if p.is_file() and INTEGRITY not in p.parents
    ]


def compute() -> dict:
    """Compute the archive Merkle root plus a flat file listing digest."""
    files = _archive_files()
    leaves = []
    listing_lines = []
    for p in files:
        rel = p.relative_to(REPO).as_posix()
        content = p.read_bytes()
        content_hash = hashlib.sha256(content).hexdigest()
        listing_lines.append(f"{rel}\t{content_hash}")
        leaves.append(leaf(rel, content))
    listing = "\n".join(listing_lines) + ("\n" if listing_lines else "")
    return {
        "v": "merkle_1",
        "algorithm": "sha256 binary Merkle; leaves domain-separated 0x00 (path\\0content), nodes 0x01; odd node promoted",
        "scope": "every file under data/ except data/integrity/",
        "root": "sha256:" + merkle_root(leaves).hex(),
        "n_files": len(files),
        "file_list_sha256": "sha256:" + hashlib.sha256(listing.encode("utf-8")).hexdigest(),
    }


def _latest_recorded() -> Path | None:
    if not INTEGRITY.exists():
        return None
    roots = sorted(INTEGRITY.glob("archive-root-*.json"))
    return roots[-1] if roots else None


def main() -> int:
    verify = "--verify" in sys.argv[1:]
    result = compute()

    if verify:
        prev = _latest_recorded()
        if prev is None:
            print("merkle: no recorded root to verify against")
            return 1
        recorded = json.loads(prev.read_text())["root"]
        ok = recorded == result["root"]
        print(f"merkle --verify: recomputed {result['root']} vs recorded {recorded} ({prev.name}) -> {'OK' if ok else 'MISMATCH'}")
        return 0 if ok else 1

    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    iso = now.isocalendar()
    result["date"] = date
    result["period"] = f"{iso.year}-w{iso.week:02d}"
    result["computed_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    INTEGRITY.mkdir(parents=True, exist_ok=True)
    out = INTEGRITY / f"archive-root-{date}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"merkle: {result['root']} over {result['n_files']} files -> {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
