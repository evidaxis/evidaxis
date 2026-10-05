"""Stage the quarterly Zenodo version of the Evidaxis record (concept DOI 10.5281/zenodo.21076011).

The deposit is the person-free publication projection of one weekly snapshot (the same
projection as the Hugging Face mirror) plus the documents that define and govern it. A git
bundle is not deposited: the raw tree and commit messages carry personal owner handles, and
a CC0 DOI cannot be withdrawn (CONSTITUTION.md, invariant 1).

    python3 scripts/zenodo_quarterly_stage.py --date 2026-10-03 --out /tmp/zenodo-q4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
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


PROJECTION = "person_free_projection_1 (scripts/hf_upload_snapshot.project_person_free)"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
OWN_DOMAIN = "@evidaxis.org"
CREATOR = {"name": "Evidaxis", "affiliation": "Evidaxis"}


def readme(date: str, snap: dict, stats: dict) -> str:
    version = snap.get("methodology_version")
    return (f"# Evidaxis Observatory — snapshot {date}\n\n"
            f"Methodology {version}, {stats['entities']} systems, period {snap.get('period')}, "
            f"source snapshot_id {snap.get('snapshot_id')}.\n\n"
            "## Files\n"
            "- `snapshot.json` — the publication projection of the weekly snapshot: systems whose name is "
            f"a personal handle appear as \"System <entity_id>\" ({stats['names_neutralized']} here), and "
            "repository links of personal accounts are omitted. Its bytes differ from the archived "
            "snapshot; `snapshot_id` names the source. `DEPOSIT-MANIFEST.json` lists the sha256 of every file.\n"
            "- `entities.csv` — one row per system with its claim URN.\n"
            "- Methodology and governance documents: the constitution, claim URN, versioning rules, "
            "methodology m3 and m4 definitions, the m4 record and the 2026-10-05 erratum.\n\n"
            "## Versions\n"
            f"These numbers are methodology {version}; methodology m4 (axis 3 counts only a system's own "
            "packages) applies from the 2026-10-10 snapshot. The erratum of 2026-10-05 lists axis-3 "
            "values whose cohort z was rounding residue in two-member cohorts (m3 snapshots 2026-09-19, "
            "2026-09-26, 2026-10-03); published values are kept as they were.\n\n"
            "## Licenses\n"
            "Data (`snapshot.json`, `entities.csv`): CC0-1.0. Methodology prose: CC-BY-4.0 "
            "(see `LICENSE-data.md`).\n\n"
            "Weekly snapshots: https://huggingface.co/datasets/evidaxis/momentum-snapshots · "
            "site: https://evidaxis.org\n")


def zenodo_metadata(date: str, snap: dict) -> dict:
    return {"title": f"Evidaxis Observatory — snapshot {date} ({snap.get('methodology_version')}, "
                     f"{len(snap.get('entities', []))} systems)",
            "upload_type": "dataset", "version": date, "license": "cc-zero",
            "creators": [dict(CREATOR)],
            "description": "Weekly measurement snapshot of open-source AI systems (person-free publication "
                           "projection), with the methodology and governance documents that define it.",
            "related_identifiers": [{"identifier": "https://evidaxis.org", "relation": "isDocumentedBy"},
                                    {"identifier": "https://huggingface.co/datasets/evidaxis/momentum-snapshots",
                                     "relation": "isSupplementTo"}]}


def check_metadata(meta: dict) -> list[str]:
    """Zenodo creators/contributors may name only the institution (CONSTITUTION.md invariant 1).
    Run on the generated file and again on a new-version draft, which inherits old metadata."""
    problems = []
    for role in ("creators", "contributors"):
        for person in meta.get(role) or []:
            if person.get("name") != "Evidaxis" or person.get("orcid") or person.get("gnd"):
                problems.append(f"{role}: {person}")
    return problems


def email_hits(folder: Path) -> list[str]:
    hits = []
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            for found in EMAIL.findall(path.read_text(encoding="utf-8", errors="replace")):
                if not found.lower().endswith(OWN_DOMAIN):
                    hits.append(f"{path.name}:{found}")
    return hits


def manifest(folder: Path, date: str, snap: dict) -> dict:
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    return {"source_snapshot_date": date, "source_snapshot_id": snap.get("snapshot_id"),
            "methodology_version": snap.get("methodology_version"), "projection": PROJECTION,
            "generator": "scripts/zenodo_quarterly_stage.py", "generator_commit": commit,
            "files": {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted(folder.rglob("*")) if path.is_file()}}


def stage(date: str, out: Path, *, project_accounts: bool = False) -> Path:
    """Strict by default: a DOI cannot be withdrawn, so project accounts (etl/project_accounts.json)
    stay masked until the decision is re-checked at a deposit (Codex consult 2026-10-05)."""
    src = SNAPSHOTS / date / "snapshot.json"
    if not src.is_file():
        raise SystemExit(f"no snapshot at {src}")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"--out must be empty: {out}")
    folder = out / f"evidaxis-snapshot-{date}"
    folder.mkdir(parents=True)
    snap = project_person_free(json.loads(src.read_text(encoding="utf-8")), project_accounts=project_accounts)
    stats = project_person_free.last_stats
    (folder / "snapshot.json").write_text(json.dumps(snap, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    entities_csv(snap, folder / "entities.csv")
    for rel in DOCS:
        target = folder / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    (folder / "README.md").write_text(readme(date, snap, stats), encoding="utf-8")
    hits = _person_free_hits(folder, project_accounts=project_accounts) + email_hits(folder)
    if hits:
        print(f"PERSON-FREE ABORT — handle or e-mail leak in staged deposit: {hits}")
        raise SystemExit(3)
    (folder / "DEPOSIT-MANIFEST.json").write_text(json.dumps(manifest(folder, date, snap), indent=2) + "\n", encoding="utf-8")
    meta = zenodo_metadata(date, snap)
    problems = check_metadata(meta)
    if problems:
        print(f"PERSON-FREE ABORT — Zenodo metadata names a person: {problems}")
        raise SystemExit(3)
    (out / "zenodo-metadata.json").write_text(json.dumps({"metadata": meta}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
    ap.add_argument("--with-project-accounts", action="store_true",
                    help="publish curated project accounts by name (only after a re-check of the decision)")
    args = ap.parse_args(argv)
    date = args.date or json.loads((REPO / "data" / "latest.json").read_text())["snapshot_date"]
    stage(date, args.out, project_accounts=args.with_project_accounts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
