#!/usr/bin/env python3
"""Upload one snapshot (publication projection) to the HF dataset
`evidaxis/momentum-snapshots`. Stdlib + huggingface-cli (pip install huggingface_hub).

Auth: HF_TOKEN in env or etl/.env. Idempotent: re-upload of the same date overwrites
that date's folder only.

    python3 scripts/hf_upload_snapshot.py [--date YYYY-MM-DD] [--dry-run]

Exit 0 on success, 3 when the person-free guard finds a handle, 1 on any other error.
--dry-run builds the stage and runs the guard. It does not upload and needs no token.
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

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.person_free import (
    FREE_TEXT_KEYS,
    classification_for,
    handle_hits,
    lenient_decoded,
    is_github_url,
    load_handle_index,
    load_owner_types,
    neutral_name,
    reveals_handle,
    safe_user_homepage,
)

REPO = _REPO_ROOT
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


def _redact_free_text(node, index, stats: dict) -> None:
    if isinstance(node, dict):
        for key in list(node.keys()):
            value = node[key]
            if key in FREE_TEXT_KEYS and isinstance(value, str) and reveals_handle(value, index):
                if key == "note":
                    node.pop(key)
                else:
                    node[key] = None
                stats["fields_redacted"] += 1
            else:
                _redact_free_text(value, index, stats)
    elif isinstance(node, list):
        for item in node:
            _redact_free_text(item, index, stats)


def _redact_packages(node, index, stats: dict) -> None:
    if isinstance(node, dict):
        package = node.get("package")
        if isinstance(package, str) and reveals_handle(package, index):
            node["package"] = "package not shown"
            stats["fields_redacted"] += 1
        for value in node.values():
            _redact_packages(value, index, stats)
    elif isinstance(node, list):
        for item in node:
            _redact_packages(item, index, stats)


def _project_entity(entity: dict, registry: dict, index, stats: dict) -> None:
    name = entity.get("name") if isinstance(entity.get("name"), str) else None
    slug = entity.get("slug") if isinstance(entity.get("slug"), str) else None
    if (name and reveals_handle(name, index)) or (slug and reveals_handle(slug, index)):
        entity_id = entity.get("entity_id")
        if isinstance(entity_id, str) and entity_id:
            entity["name"] = neutral_name(entity_id)
            entity["slug"] = entity_id.lower()
        else:
            entity.pop("name", None)
            entity.pop("slug", None)
        stats["names_neutralized"] += 1
        stats["fields_redacted"] += 1

    github_repo = entity.get("github_repo")
    if github_repo:
        entry = classification_for(github_repo, registry)
        canonical = entry["full_name"]
        owner, repo_name = canonical.split("/", 1)
        if entry["owner_type"] == "User":
            hidden = reveals_handle(repo_name, index)
            entity["repository"] = {
                "repo_name": None if hidden else repo_name,
                "owner_type": "user",
                "repo_ref": f"gh:{entry['repo_id']}",
            }
            if hidden:
                stats["fields_redacted"] += 1
            entity.pop("github_repo", None)
            homepage = entity.get("homepage") if isinstance(entity.get("homepage"), str) else None
            # After a transfer the stored owner can still sit in the homepage (review 2026-10-04).
            safe = safe_user_homepage(homepage, (owner, github_repo.split("/", 1)[0]))
            if homepage and safe is None:
                stats["fields_redacted"] += 1
                entity.pop("homepage", None)
            elif safe:
                entity["homepage"] = safe
        else:
            entity["github_repo"] = canonical
            homepage = entity.get("homepage") if isinstance(entity.get("homepage"), str) else None
            if homepage and is_github_url(homepage):
                rewritten = f"https://github.com/{canonical}"
                if rewritten != homepage and reveals_handle(homepage, index):
                    stats["fields_redacted"] += 1
                entity["homepage"] = rewritten

    _redact_free_text(entity, index, stats)
    _redact_packages(entity, index, stats)


def project_person_free(snap: dict, *, project_accounts: bool = True) -> dict:
    """Publication projection, same rules as web/src/lib/person_free.ts plus the
    name/slug neutralization applied when the site loads a snapshot.

    User-owned repositories drop ``github_repo`` and any homepage that is a GitHub
    URL or carries that owner's handle. A repository name that is itself a handle
    is omitted. Organization repositories keep the canonical ``full_name``, and a
    GitHub homepage is rewritten to that name. A name or slug that reveals a
    handle becomes ``System <entity_id>``. A deps.dev package name that reveals a
    handle becomes ``package not shown``. Free text that reveals a handle is dropped.
    """
    index, _stale = load_handle_index(REPO, project_accounts=project_accounts)
    registry = load_owner_types(REPO, project_accounts=project_accounts)
    out = json.loads(json.dumps(snap))
    stats = {"entities": 0, "names_neutralized": 0, "fields_redacted": 0}
    for entity in out.get("entities", []):
        stats["entities"] += 1
        _project_entity(entity, registry, index, stats)
    project_person_free.last_stats = stats
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


def _person_free_hits(folder: Path, *, project_accounts: bool = True) -> list[str]:
    """Fail-closed scan of the staged upload. Handle matching is exact
    (scripts/person_free.py). Moved repositories also reject the exact stale
    ``owner/repo`` path."""
    index, stale_paths = load_handle_index(REPO, project_accounts=project_accounts)
    hits: list[str] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        blob = path.read_text(encoding="utf-8", errors="replace")
        found = handle_hits(blob, index)
        for handle in handle_hits(lenient_decoded(blob), index):  # percent-encoded leaks
            if handle not in found:
                found.append(handle)
        lower = blob.lower()
        seen = set(found)
        for stale in stale_paths:
            if re.search(rf"(?<![a-z0-9_.-]){re.escape(stale)}(?![a-z0-9_.-])", lower) and stale not in seen:
                found.append(stale)
                seen.add(stale)
        hits.extend(f"{path.name}:{handle}" for handle in found)
    return hits


def _assert_person_free(folder: Path) -> None:
    hits = _person_free_hits(folder)
    if hits:
        exc = SystemExit(f"PERSON-FREE ABORT — handle leak in staged upload: {hits}")
        exc.code = 3
        raise exc


def _summary(date: str, stats: dict, guard_hits: int) -> str:
    return (
        f"dry-run {date}: entities={stats['entities']} "
        f"names_neutralized={stats['names_neutralized']} "
        f"fields_redacted={stats['fields_redacted']} guard_hits={guard_hits}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    date = args.date or sorted(p.name for p in SNAPSHOTS.iterdir() if p.is_dir())[-1]
    src = SNAPSHOTS / date
    if not (src / "snapshot.json").is_file():
        print(f"no snapshot at {src}")
        return 4
    tok = ""
    cli_name = ""
    if not args.dry_run:
        tok = _load_token()
        if not tok:
            print("HF_TOKEN missing (env or etl/.env) — cannot upload")
            return 4
        # huggingface_hub >=1.0 ships the `hf` CLI; `huggingface-cli upload` is deprecated
        # and fails on recent versions. Prefer `hf`, fall back to the legacy name.
        cli = shutil.which("hf") or shutil.which("huggingface-cli")
        if not cli:
            print("hf CLI not found: pip install -U huggingface_hub")
            return 4
        cli_name = Path(cli).name

    try:
        snap = project_person_free(json.loads((src / "snapshot.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(exc)  # projection or classification failure: never a silent warning
        return 4
    stats = project_person_free.last_stats
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
        hits = _person_free_hits(stage.parent)
        if args.dry_run or hits:
            print(_summary(date, stats, len(hits)))
        if hits:
            print(f"PERSON-FREE ABORT — handle leak in staged upload: {hits}", file=sys.stderr)
            return 3
        if args.dry_run:
            return 0
        env = dict(os.environ, HF_TOKEN=tok)
        for upload_args in ([str(stage), date], [str(Path(td) / "README.md"), "README.md"]):
            result = subprocess.run([cli_name, "upload", DATASET, *upload_args,
                                     "--repo-type", "dataset"], env=env)
            if result.returncode != 0:
                print("upload failed")
                return 5
    print(f"uploaded {date} + card to hf.co/datasets/{DATASET}")
    return 0


if __name__ == "__main__":
    # Exit codes: 0 ok · 5 upload/network failure (the only warning in CI) · 3 person-free
    # abort · 4 classification/projection/configuration failure · 2 usage error. Python's
    # own crash code (1, e.g. an import error) therefore also fails CI, never warns.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # an unexpected crash must not read as a network warning
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(4)
