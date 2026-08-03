"""Activation closes queue slots and preserves repository identity."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import activation_tranche as activation


def _write_inputs(tmp_path, monkeypatch, members, entities, registry=None):
    month_dir = tmp_path / "data" / "census" / "2026-09"
    month_dir.mkdir(parents=True)
    manifest_path = month_dir / "pending-manifest.json"
    manifest_path.write_text(json.dumps({"members": members}))

    seeds_path = tmp_path / "etl" / "seeds.json"
    seeds_path.parent.mkdir()
    seeds_path.write_text(json.dumps({
        "meta": {},
        "verticals": {
            "existing": {
                "label": "Existing",
                "industry_slug": "ai",
                "subniche_slug": "existing",
                "entities": entities,
            }
        },
    }))
    if registry is not None:
        registry_path = tmp_path / "data" / "registry_ids.json"
        registry_path.write_text(json.dumps({"members": registry}))

    monkeypatch.setattr(activation, "REPO", tmp_path)
    monkeypatch.setattr(activation, "SEEDS", seeds_path)
    monkeypatch.setattr(
        sys, "argv", ["activation_tranche.py", "--month", "2026-09", "--apply"]
    )
    return manifest_path, seeds_path


def _live(repo_id, full_name, stars):
    return {
        "id": repo_id,
        "full_name": full_name,
        "stars": stars,
        "archived": False,
        "fork": False,
    }


def test_apply_marks_unavailable_and_excludes_terminal_status_from_pending(
        tmp_path, monkeypatch):
    members = [
        {"repo_id": 1, "full_name": "group/ready", "status": "pending"},
        {"repo_id": 2, "full_name": "group/gone", "status": "pending"},
        {
            "repo_id": 3,
            "full_name": "group/already-gone",
            "status": "unavailable",
            "unavailable_on": "2026-08-01",
        },
    ]
    manifest_path, _ = _write_inputs(tmp_path, monkeypatch, members, [])
    monkeypatch.setattr(
        activation,
        "gh_repos_batch",
        lambda _names: {"group/ready": _live(1, "group/ready", 900)},
    )

    assert activation.main() == 0

    manifest = json.loads(manifest_path.read_text())
    by_id = {member["repo_id"]: member for member in manifest["members"]}
    assert by_id[1]["status"] == "activated"
    assert by_id[2]["status"] == "unavailable"
    assert by_id[2]["unavailable_on"]
    assert by_id[3]["unavailable_on"] == "2026-08-01"
    assert not [member for member in manifest["members"]
                if member["status"] == "pending"]

    tranche_path = next((manifest_path.parent / "tranches").glob(
        "*-tranche.json"
    ))
    tranche = json.loads(tranche_path.read_text())
    assert tranche["pending_before"] == 2
    assert tranche["skipped_unavailable"] == ["group/gone"]


def test_apply_deduplicates_renamed_seed_by_repository_id(tmp_path, monkeypatch):
    members = [
        {"repo_id": 42, "full_name": "new-group/project", "status": "pending"}
    ]
    entities = [{
        "github_repo": "old-group/project",
        "entity_type": "repo",
        "name": "project",
        "openalex_work_ids": [],
    }]
    registry = {
        "old-group/project": {
            "repo_id": 42,
            "canonical": "new-group/project",
            "cohort": "existing",
        }
    }
    manifest_path, seeds_path = _write_inputs(
        tmp_path, monkeypatch, members, entities, registry
    )
    monkeypatch.setattr(
        activation,
        "gh_repos_batch",
        lambda _names: {
            "new-group/project": _live(42, "new-group/project", 800)
        },
    )

    assert activation.main() == 0

    seeds = json.loads(seeds_path.read_text())
    repos = [
        entity["github_repo"]
        for vertical in seeds["verticals"].values()
        for entity in vertical["entities"]
    ]
    assert repos == ["old-group/project"]
    manifest = json.loads(manifest_path.read_text())
    assert manifest["members"][0]["status"] == "activated"
