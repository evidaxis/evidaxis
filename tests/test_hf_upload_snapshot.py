"""Publication regressions for confirmed personal-to-organization transfers."""
import json
import pytest

from scripts import hf_upload_snapshot as hf


@pytest.fixture
def publication_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "etl").mkdir(parents=True)
    handles = repo / "web/src/data/person-free-handles.json"
    handles.parent.mkdir(parents=True)
    handles.write_bytes((hf.REPO / "web/src/data/person-free-handles.json").read_bytes())
    (repo / "etl/owner_types.json").write_text(json.dumps({
        "schema_version": "owner_types_1",
        "repos": {
            "mensfeld/code-on-incus": {
                "owner_type": "Organization", "repo_id": 1129585228, "full_name": "coipond/coi",
            },
            "current-person/tool": {
                "owner_type": "User", "repo_id": 7, "full_name": "current-person/tool",
            },
        },
    }))
    monkeypatch.setattr(hf, "REPO", repo)
    return repo


@pytest.mark.parametrize(("homepage", "expected"), [
    ("https://github.com/mensfeld/code-on-incus", "https://github.com/coipond/coi"),
    ("https://www.GitHub.com/mensfeld/code-on-incus?tab=readme#top", "https://github.com/coipond/coi"),
    ("https://coipond.ai", "https://coipond.ai"),
    ("https://github.com.example.test/project", "https://github.com.example.test/project"),
    (None, None),
])
def test_confirmed_transfer_projects_homepage_without_mutating_archive(publication_repo, tmp_path, homepage, expected):
    original = {"entities": [{
        "entity_id": "e_WJWEQY59YG9", "github_repo": "mensfeld/code-on-incus", "homepage": homepage,
    }]}
    before = json.dumps(original)
    projected = hf.project_person_free(original)
    assert projected["entities"] == [{
        "entity_id": "e_WJWEQY59YG9", "github_repo": "coipond/coi", "homepage": expected,
    }]
    assert json.dumps(original) == before
    assert "mensfeld" not in json.dumps(projected)
    stage = tmp_path / "upload"
    stage.mkdir()
    (stage / "snapshot.json").write_text(json.dumps(projected))
    hf._assert_person_free(stage)


@pytest.mark.parametrize("leak", [
    "mensfeld", "MENSFELD", "@mensfeld", "https://github.com/mensfeld/code-on-incus",
])
@pytest.mark.parametrize("retained_in_cache", [True, False])
def test_former_personal_owner_stays_banned(publication_repo, tmp_path, leak, retained_in_cache):
    if not retained_in_cache:
        cache_path = publication_repo / "etl/owner_types.json"
        cache = json.loads(cache_path.read_text())
        cache["repos"].pop("mensfeld/code-on-incus")
        cache_path.write_text(json.dumps(cache))
    stage = tmp_path / "upload"
    stage.mkdir()
    (stage / "snapshot.json").write_text(json.dumps({"homepage": leak}))
    with pytest.raises(SystemExit, match="mensfeld"):
        hf._assert_person_free(stage)


def test_user_owned_projection_and_guard_remain_active(publication_repo, tmp_path):
    projected = hf.project_person_free({"entities": [{
        "github_repo": "current-person/tool", "homepage": "https://github.com/current-person/tool",
    }]})
    assert projected == {"entities": [{
        "repository": {"repo_name": "tool", "owner_type": "user", "repo_ref": "gh:7"},
    }]}
    stage = tmp_path / "upload"
    stage.mkdir()
    (stage / "snapshot.json").write_text(json.dumps(projected))
    hf._assert_person_free(stage)
    (stage / "snapshot.json").write_text("current-person")
    with pytest.raises(SystemExit, match="current-person"):
        hf._assert_person_free(stage)
