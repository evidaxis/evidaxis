#!/usr/bin/env python3
"""Upload the latest snapshot (publication projection) to the HF dataset
`evidaxis/momentum-snapshots`. Stdlib + huggingface-cli (pip install huggingface_hub).

Auth: HF_TOKEN in env or etl/.env. Idempotent: re-upload of the same date overwrites
that date's folder only. Run: python3 scripts/hf_upload_snapshot.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAPSHOTS = REPO / "data" / "snapshots"
CARD = REPO / "distribution" / "hf" / "README.md"
DATASET = "evidaxis/momentum-snapshots"


def _load_token() -> str:
    tok = os.environ.get("HF_TOKEN", "").strip()
    if not tok:
        env = REPO / "etl" / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*HF_TOKEN\s*=\s*(\S+)", line)
                if m:
                    tok = m.group(1).strip().strip('"').strip("'")
    return tok


def project_person_free(snap: dict) -> dict:
    """Publication projection: user-owned repo slugs are already absent from the
    web layer; the archive file still carries them (internal natural key), so the
    HF mirror strips `github_repo`/github homepage for entities whose owner is a
    User per etl/owner_types.json (same policy as web/src/lib/person_free.ts)."""
    types = json.loads((REPO / "etl" / "owner_types.json").read_text(encoding="utf-8"))["repos"]
    out = json.loads(json.dumps(snap))  # deep copy
    for e in out.get("entities", []):
        repo = e.get("github_repo")
        entry = types.get(repo)
        if not entry:
            continue
        canonical = entry.get("full_name", repo)
        if entry.get("owner_type") == "User":
            e["repository"] = {"repo_name": canonical.split("/")[1],
                               "owner_type": "user", "repo_ref": f"gh:{entry['repo_id']}"}
            e.pop("github_repo", None)
            # Strip any homepage that is a code-forge URL OR carries the owner handle
            # (github.com, huggingface.co/<user>, personal .io, etc.) — matches the web
            # person_free.ts safeUserHomepage policy. Owner handle from BOTH stored slug
            # and canonical full_name (transfers).
            hp = str(e.get("homepage") or "").lower()
            owners = {repo.split("/")[0].lower(), canonical.split("/")[0].lower()}
            forge = any(h in hp for h in ("github.com", "gitlab.com", "huggingface.co"))
            if hp and (forge or any(o in hp for o in owners)):
                e.pop("homepage", None)
        elif canonical != repo:
            e["github_repo"] = canonical
    return out


def entities_csv(snap: dict, path: Path) -> None:
    rows = []
    for e in snap.get("entities", []):
        ax = e.get("axes", {})
        rows.append({
            "entity_id": e.get("entity_id"), "name": e.get("name"),
            "cohort": e.get("cohort"), "status": e.get("status"),
            "momentum": e.get("momentum"),
            "velocity_z": (ax.get("github_commit_velocity") or {}).get("cohort_z"),
            "citation_z": (ax.get("openalex_citation_momentum") or {}).get("cohort_z"),
            "claim_urn": f"urn:evidaxis:claim:{e.get('entity_id')}:"
                         f"{snap.get('methodology_version')}:{snap.get('snapshot_date')}",
        })
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _assert_person_free(folder: Path) -> None:
    """Fail-closed: no User-owned handle (stored OR canonical owner segment) may
    appear anywhere in the staged upload. Would have caught the 2026-07-11 homepage
    and provenance leaks."""
    types = json.loads((REPO / "etl" / "owner_types.json").read_text(encoding="utf-8"))["repos"]
    handles = set()
    for repo, v in types.items():
        if v.get("owner_type") == "User":
            handles.add(repo.split("/")[0].lower())
            handles.add(v.get("full_name", repo).split("/")[0].lower())
    hits = []
    for f in folder.rglob("*"):
        if not f.is_file():
            continue
        blob = f.read_text(encoding="utf-8", errors="replace").lower()
        for h in handles:
            if h in blob:
                hits.append(f"{f.name}:{h}")
    if hits:
        raise SystemExit(f"PERSON-FREE ABORT — handle leak in staged upload: {hits}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or sorted(p.name for p in SNAPSHOTS.iterdir() if p.is_dir())[-1]
    src = SNAPSHOTS / date
    if not (src / "snapshot.json").is_file():
        print(f"no snapshot at {src}"); return 1
    tok = _load_token()
    if not tok:
        print("HF_TOKEN missing (env or etl/.env) — cannot upload"); return 1
    if not shutil.which("huggingface-cli"):
        print("huggingface-cli not found: pip install -U huggingface_hub"); return 1

    snap = project_person_free(json.loads((src / "snapshot.json").read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / date
        stage.mkdir()
        (stage / "snapshot.json").write_text(json.dumps(snap, indent=1, ensure_ascii=False),
                                             encoding="utf-8")
        entities_csv(snap, stage / "entities.csv")
        # NOTE: manifest.json / provenance.json are NOT mirrored — they carry the RAW
        # capture layer (github_repos list with personal slugs). The verification chain
        # lives in the canonical git/Zenodo archive (see README). HF = publication
        # projection only: projected snapshot.json + entities.csv.
        shutil.copy(CARD, Path(td) / "README.md")
        _assert_person_free(stage.parent)
        env = dict(os.environ, HF_TOKEN=tok)
        for args_ in ([str(stage), date], [str(Path(td) / "README.md"), "README.md"]):
            r = subprocess.run(["huggingface-cli", "upload", DATASET, *args_,
                                "--repo-type", "dataset"], env=env)
            if r.returncode != 0:
                print("upload failed"); return 1
    print(f"uploaded {date} + card to hf.co/datasets/{DATASET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
