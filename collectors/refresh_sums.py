"""refresh_sums - recompute a snapshot's SHA256SUMS after sanctioned post-steps.

Why this exists: etl/collect.py (byte-frozen) writes SHA256SUMS as part of its
run, but the weekly pipeline then applies sanctioned, deterministic post-steps
(etl/reclass_pre_spine.py, collectors/taxonomy_v2.py) that mutate snapshot.json
and manifest.json. Without a final re-hash the published bundle ships checksums
that fail against its own bytes - the exact defect found in the 2026-07-01
snapshot (see that folder's ERRATA.md). This script is the mandatory FINAL
content step of any pipeline that touches snapshot files: nothing may mutate
the snapshot after it runs.

It never touches snapshot.json / manifest.json / provenance.json themselves -
only the SHA256SUMS witness file is rewritten to match the actual bytes.

New code, lives OUTSIDE the frozen etl/. Pure standard library.

Usage:
  python collectors/refresh_sums.py --date YYYY-MM-DD   # rewrite that snapshot's SHA256SUMS
  python collectors/refresh_sums.py --verify            # check EVERY data/snapshots/*/SHA256SUMS (exit 1 on any mismatch)
"""
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAPSHOTS = REPO / "data" / "snapshots"

# The canonical bundle files, in the exact order frozen into etl/collect.py.
BUNDLE = ("snapshot.json", "manifest.json", "provenance.json")
# dropped.json joins the pinned set FORWARD-ONLY from the cutover date (live-sweep
# 2026-07-10: advertised but unpinned). Published SHA256SUMS are append-only frozen —
# never rewritten retroactively.
FORWARD_EXTRAS = (("dropped.json", "2026-07-11"),)


def _sums_text(snap_dir: Path) -> str:
    """SHA256SUMS content for a snapshot dir, byte-identical to collect.py's format."""
    lines = []
    names = list(BUNDLE) + [fn for fn, since in FORWARD_EXTRAS
                            if snap_dir.name >= since and (snap_dir / fn).is_file()]
    for fn in names:
        h = hashlib.sha256((snap_dir / fn).read_bytes()).hexdigest()
        lines.append(f"{h}  {fn}")
    return "\n".join(lines) + "\n"


def refresh(date: str) -> int:
    snap_dir = SNAPSHOTS / date
    if not snap_dir.is_dir():
        print(f"refresh_sums: no snapshot dir {snap_dir.relative_to(REPO)}")
        return 1
    sums_path = snap_dir / "SHA256SUMS"
    new = _sums_text(snap_dir)
    old = sums_path.read_text() if sums_path.exists() else ""
    if new == old:
        print(f"refresh_sums: {date} already consistent (no-op)")
        return 0
    sums_path.write_text(new)
    print(f"refresh_sums: {date} SHA256SUMS rewritten to match actual bytes")
    return 0


def verify_all() -> int:
    """shasum -c over every snapshot folder, driven by each folder's own SHA256SUMS."""
    bad = 0
    dirs = sorted(p for p in SNAPSHOTS.iterdir() if p.is_dir()) if SNAPSHOTS.is_dir() else []
    if not dirs:
        print("refresh_sums --verify: no snapshot dirs found")
        return 1
    for snap_dir in dirs:
        dir_bad = 0
        sums_path = snap_dir / "SHA256SUMS"
        if not sums_path.exists():
            print(f"  {snap_dir.name}: SHA256SUMS MISSING")
            bad += 1
            continue
        for line in sums_path.read_text().splitlines():
            if not line.strip():
                continue
            recorded, fn = line.split(None, 1)
            fn = fn.strip()
            f = snap_dir / fn
            if not f.exists():
                print(f"  {snap_dir.name}/{fn}: FILE MISSING")
                dir_bad += 1
                continue
            actual = hashlib.sha256(f.read_bytes()).hexdigest()
            if actual != recorded:
                print(f"  {snap_dir.name}/{fn}: MISMATCH recorded {recorded[:12]}… actual {actual[:12]}…")
                dir_bad += 1
        bad += dir_bad
        print(f"  {snap_dir.name}: {'OK' if dir_bad == 0 else f'{dir_bad} mismatch(es)'}")
    print(f"refresh_sums --verify: {len(dirs)} snapshot dirs, {bad} mismatches -> {'OK' if bad == 0 else 'FAILED'}")
    return 0 if bad == 0 else 1


def main() -> int:
    args = sys.argv[1:]
    if "--verify" in args:
        return verify_all()
    if "--date" in args:
        i = args.index("--date")
        if i + 1 >= len(args):
            print("refresh_sums: --date requires YYYY-MM-DD")
            return 2
        return refresh(args[i + 1])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
