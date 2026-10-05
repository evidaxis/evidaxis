"""Stage the quarterly Zenodo version of the Evidaxis record (concept DOI 10.5281/zenodo.21076011).

The deposit is the person-free publication projection of one weekly snapshot (the same
projection as the Hugging Face mirror) plus the documents that define and govern it. A git
bundle is not deposited: the raw tree and commit messages carry personal owner handles, and
a CC0 DOI cannot be withdrawn (CONSTITUTION.md, invariant 1).

    python3 scripts/zenodo_quarterly_stage.py --date 2026-10-03 --out /tmp/zenodo-q4
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.hf_upload_snapshot import _person_free_hits, entities_csv, project_person_free  # noqa: E402

SNAPSHOTS = REPO / "data" / "snapshots"
DOCS = ("CONSTITUTION.md", "CLAIM-URN.md", "METHODOLOGY-VERSIONING.md", "LICENSE-data.md",
        "methodology/m3.json", "methodology/m4.json",
        "governance/METHODOLOGY-M4-2026-10-04.md",
        "governance/ERRATUM-2026-10-05-axis3-two-member-rounding.md")


def readme(date: str, snap: dict, stats: dict) -> str:
    return (f"# Evidaxis Observatory — snapshot {date}\n\n"
            f"Methodology {snap.get('methodology_version')}, {stats['entities']} systems, "
            f"period {snap.get('period')}, snapshot_id {snap.get('snapshot_id')}.\n\n"
            "Files: `snapshot.json` (publication projection: systems whose name is a personal "
            f"handle appear as \"System <entity_id>\" — {stats['names_neutralized']} here — and "
            "repository links of personal accounts are omitted), `entities.csv` (one row per "
            "system with its claim URN), and the documents that define the methodology, the "
            "claim URN, versioning and errata.\n\n"
            "Weekly snapshots: https://huggingface.co/datasets/evidaxis/momentum-snapshots · "
            "site: https://evidaxis.org · license: CC0-1.0.\n")


def stage(date: str, out: Path) -> Path:
    src = SNAPSHOTS / date / "snapshot.json"
    if not src.is_file():
        raise SystemExit(f"no snapshot at {src}")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"--out must be empty: {out}")
    folder = out / f"evidaxis-snapshot-{date}"
    folder.mkdir(parents=True)
    snap = project_person_free(json.loads(src.read_text(encoding="utf-8")))
    stats = project_person_free.last_stats
    (folder / "snapshot.json").write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    entities_csv(snap, folder / "entities.csv")
    for rel in DOCS:
        target = folder / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    (folder / "README.md").write_text(readme(date, snap, stats), encoding="utf-8")
    hits = _person_free_hits(folder)
    if hits:
        print(f"PERSON-FREE ABORT — handle leak in staged deposit: {hits}")
        raise SystemExit(3)
    archive = out / f"evidaxis-snapshot-{date}-deposit.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(folder))
    print(f"staged {archive} entities={stats['entities']} names_neutralized={stats['names_neutralized']} "
          f"fields_redacted={stats['fields_redacted']} guard_hits=0")
    return archive


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=None)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    date = args.date or json.loads((REPO / "data" / "latest.json").read_text())["snapshot_date"]
    stage(date, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
