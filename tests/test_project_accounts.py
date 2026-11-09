"""Project accounts are published like organization repositories.

The owner-types file on disk stays User. The loader applies the override.
"""
import json
from pathlib import Path

from scripts import hf_upload_snapshot as hf
from scripts.person_free import load_owner_types

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "data" / "snapshots" / "2026-10-03" / "snapshot.json"


def _accounts() -> dict:
    document = json.loads((REPO / "etl" / "project_accounts.json").read_text(encoding="utf-8"))
    return document["accounts"]


def test_load_owner_types_marks_each_project_account():
    accounts = _accounts()
    assert len(accounts) == 10
    # loaders match the lower-cased canonical owner; a mixed-case key would silently stay masked
    assert all(handle == handle.lower() for handle in accounts)
    registry = load_owner_types(REPO)
    raw = json.loads((REPO / "etl" / "owner_types.json").read_text(encoding="utf-8"))["repos"]
    for meta in accounts.values():
        repo = meta["repo"]
        entry = registry[repo]
        assert entry["owner_type"] == "Organization"
        assert entry["github_owner_type"] == "User"
        assert entry["publication_basis"] == "project_account"
        assert entry["repo_id"] == raw[repo]["repo_id"]
        assert entry["full_name"] == raw[repo]["full_name"]
        assert raw[repo]["owner_type"] == "User"
        assert set(raw[repo]) == {"owner_type", "repo_id", "full_name"}


def test_projection_keeps_project_account_names_and_neutralizes_twelve():
    accounts = _accounts()
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    original = {entity["entity_id"]: entity for entity in snap["entities"]}
    projected = hf.project_person_free(snap)
    assert hf.project_person_free.last_stats["names_neutralized"] == 12
    by_id = {entity["entity_id"]: entity for entity in projected["entities"]}
    # Rule c also covers former owners of rows that are now Organization-owned.
    assert by_id["e_RYZNSTS8RB1"]["name"] == "System e_RYZNSTS8RB1"
    assert by_id["e_RYZNSTS8RB1"]["slug"] == "e_ryznsts8rb1"
    # Dependency-only token matching must not neutralize hyphenated prose names.
    for entity_id in ("e_C7XBRXBQQ1A", "e_SZKD4NSDYWH", "e_P8DR6F4BC0K",
                      "e_R60YV8ENRHB", "e_25NRZ6KAYTE", "e_34ZSW4G3AHD"):
        assert by_id[entity_id]["name"] == original[entity_id]["name"]
        assert by_id[entity_id]["slug"] == original[entity_id]["slug"]
        assert by_id[entity_id]["repository"]["repo_name"] == original[entity_id]["github_repo"].split('/')[1]
    for meta in accounts.values():
        entity_id = meta["entity_id"]
        assert by_id[entity_id]["name"] == original[entity_id]["name"]


def test_empty_accounts_map_neutralizes_22(monkeypatch):
    monkeypatch.setattr("scripts.person_free.load_project_accounts", lambda _repo: {})
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    hf.project_person_free(snap)
    assert hf.project_person_free.last_stats["names_neutralized"] == 22


def test_missing_accounts_file_leaves_user_types(tmp_path):
    raw = json.loads((REPO / "etl" / "owner_types.json").read_text(encoding="utf-8"))
    etl = tmp_path / "etl"
    etl.mkdir()
    (etl / "owner_types.json").write_text(json.dumps(raw), encoding="utf-8")
    registry = load_owner_types(tmp_path)
    for meta in _accounts().values():
        entry = registry[meta["repo"]]
        assert entry["owner_type"] == "User"
        assert "github_owner_type" not in entry
        assert "publication_basis" not in entry
