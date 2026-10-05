"""The quarterly Zenodo package is the person-free projection; a leaked handle stops it."""
import json
import zipfile
from pathlib import Path

import pytest

from scripts import zenodo_quarterly_stage as z

REPO = Path(__file__).resolve().parent.parent


def test_stage_latest_is_person_free(tmp_path):
    date = json.loads((REPO / "data" / "latest.json").read_text())["snapshot_date"]
    archive = z.stage(date, tmp_path / "out")
    names = zipfile.ZipFile(archive).namelist()
    assert {"snapshot.json", "entities.csv", "README.md", "CONSTITUTION.md", "DEPOSIT-MANIFEST.json"} <= set(names)
    meta = json.loads((tmp_path / "out" / "zenodo-metadata.json").read_text())["metadata"]
    assert [c["name"] for c in meta["creators"]] == ["Evidaxis"] and z.check_metadata(meta) == []
    assert not any(n.startswith(("manifest", "provenance")) for n in names)


def test_leaked_handle_stops_the_package(tmp_path, monkeypatch):
    from scripts.person_free import load_owner_types
    user_repo = next(e["full_name"] for e in load_owner_types(REPO).values()
                     if isinstance(e, dict) and e.get("owner_type") == "User")
    real_readme = z.readme
    monkeypatch.setattr(z, "readme", lambda *a: real_readme(*a) + f"\nsee github.com/{user_repo}\n")
    date = json.loads((REPO / "data" / "latest.json").read_text())["snapshot_date"]
    with pytest.raises(SystemExit) as exc:
        z.stage(date, tmp_path / "out")
    assert exc.value.code == 3
    assert not list((tmp_path / "out").glob("*.zip"))


def test_foreign_email_stops_the_package(tmp_path, monkeypatch):
    real_readme = z.readme
    monkeypatch.setattr(z, "readme", lambda *a: real_readme(*a) + "\ncontact: someone@example.com\n")
    date = json.loads((REPO / "data" / "latest.json").read_text())["snapshot_date"]
    with pytest.raises(SystemExit) as exc:
        z.stage(date, tmp_path / "out")
    assert exc.value.code == 3


def test_inherited_person_in_metadata_is_refused():
    meta = {"creators": [{"name": "Evidaxis"}], "contributors": [{"name": "Some Person", "type": "Other"}]}
    assert z.check_metadata(meta)
