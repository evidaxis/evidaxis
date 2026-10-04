"""Publication regressions for confirmed personal-to-organization transfers."""
import json
import pytest

from scripts import hf_upload_snapshot as hf
from scripts.person_free import build_handle_index, handle_hits


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


# Parity with web/src/lib/personFree.test.ts. Handles here are synthetic.
_SCALE = build_handle_index(["f", "av", "78", "100", "e", "synth-owner", "longhandle", "q00"])


def test_short_or_numeric_handles_ignore_ordinary_text():
    ordinary = "A free weekly archive of 100 systems, 78 of them with a figure; av. commits"
    paths = '<a href="/e/e_ZZZKJHG7Q9A/">agentmemory</a> /ai/cohorts/x/page/100/'
    assert handle_hits(ordinary, _SCALE) == []
    assert handle_hits(paths, _SCALE) == []
    assert handle_hits("code q00", _SCALE) == []


def test_handle_in_repository_slug_and_github_url():
    assert handle_hits("synth-owner/widget", _SCALE) == ["synth-owner"]
    assert handle_hits("https://github.com/synth-owner/widget", _SCALE) == ["synth-owner"]
    assert handle_hits("https://api.github.com/repos/synth-owner/widget", _SCALE) == ["synth-owner"]
    assert handle_hits("see https://github.com/f/repo and https://github.com/100/x", _SCALE) == ["f", "100"]
    assert handle_hits("https://github.com/q00/x", _SCALE) == ["q00"]


def test_mention_and_standalone_distinctive_handle():
    assert handle_hits("thanks @AV", _SCALE) == ["av"]
    assert handle_hits("Built by Synth-Owner.", _SCALE) == ["synth-owner"]
    assert handle_hits("LONGHANDLE model", _SCALE) == ["longhandle"]


def test_distinctive_handle_inside_longer_token_does_not_match():
    assert handle_hits("longhandling and synth-owner-fan", _SCALE) == []


def _tiny_repo(tmp_path, repos):
    repo = tmp_path / "repo"
    (repo / "etl").mkdir(parents=True)
    data = repo / "web/src/data"
    data.mkdir(parents=True)
    (data / "person-free-handles.json").write_text("[]")
    (repo / "etl/owner_types.json").write_text(json.dumps({
        "schema_version": "owner_types_1",
        "repos": repos,
    }))
    return repo


def test_guard_ignores_ordinary_text_and_catches_a_real_handle(tmp_path, monkeypatch):
    repo = _tiny_repo(tmp_path, {
        "f/widget": {"owner_type": "User", "repo_id": 1, "full_name": "f/widget"},
        "av/widget": {"owner_type": "User", "repo_id": 2, "full_name": "av/widget"},
        "78/widget": {"owner_type": "User", "repo_id": 3, "full_name": "78/widget"},
        "100/widget": {"owner_type": "User", "repo_id": 4, "full_name": "100/widget"},
        "synth-owner/widget": {"owner_type": "User", "repo_id": 5, "full_name": "synth-owner/widget"},
    })
    monkeypatch.setattr(hf, "REPO", repo)
    stage = tmp_path / "upload"
    stage.mkdir()
    blob = stage / "snapshot.json"
    blob.write_text("A free weekly archive of 100 systems, 78 of them with a figure; av. commits")
    hf._assert_person_free(stage)
    blob.write_text("synth-owner/widget")
    with pytest.raises(SystemExit, match="synth-owner") as caught:
        hf._assert_person_free(stage)
    assert caught.value.code == 3
    blob.write_text("thanks @synth-owner")
    with pytest.raises(SystemExit, match="synth-owner"):
        hf._assert_person_free(stage)
    blob.write_text("Built by Synth-Owner.")
    with pytest.raises(SystemExit, match="synth-owner"):
        hf._assert_person_free(stage)


def test_projection_neutralizes_handle_name_and_package_label(tmp_path, monkeypatch):
    repo = _tiny_repo(tmp_path, {
        "synth-owner/synth-owner": {
            "owner_type": "User", "repo_id": 11, "full_name": "synth-owner/synth-owner",
        },
        "example-org/widget": {
            "owner_type": "Organization", "repo_id": 12, "full_name": "example-org/widget",
        },
    })
    monkeypatch.setattr(hf, "REPO", repo)
    original = {"entities": [
        {
            "entity_id": "e_SYNTH0001",
            "name": "Synth-Owner",
            "slug": "synth-owner",
            "github_repo": "synth-owner/synth-owner",
            "homepage": "https://github.com/synth-owner/synth-owner",
            "note": "maintained as synth-owner",
            "deps": {"system": "pypi", "package": "synth-owner"},
        },
        {
            "entity_id": "e_ORG0000001",
            "name": "Widget",
            "slug": "widget",
            "github_repo": "example-org/widget",
            "homepage": "https://example.org",
            "deps": {"system": "pypi", "package": "torch"},
        },
    ]}
    before = json.dumps(original)
    projected = hf.project_person_free(original)
    assert json.dumps(original) == before
    masked = projected["entities"][0]
    assert masked["name"] == "System e_SYNTH0001"
    assert masked["slug"] == "e_synth0001"
    assert masked["deps"]["package"] == "package not shown"
    assert "note" not in masked
    assert "github_repo" not in masked
    assert masked["repository"]["repo_name"] is None
    assert "synth-owner" not in json.dumps(projected).lower()
    kept = projected["entities"][1]
    assert kept["name"] == "Widget"
    assert kept["github_repo"] == "example-org/widget"
    assert kept["homepage"] == "https://example.org"
    assert kept["deps"]["package"] == "torch"
    stage = tmp_path / "upload"
    stage.mkdir()
    (stage / "snapshot.json").write_text(json.dumps(projected))
    hf._assert_person_free(stage)


@pytest.mark.parametrize("date", ["2026-10-03", "2026-09-26", "2026-09-19"])
def test_dry_run_real_snapshot_has_zero_guard_hits(date, capsys):
    assert hf.main(["--date", date, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert f"dry-run {date}:" in out
    assert "guard_hits=0" in out


# ---------------------------------------------------------------- review fixes 2026-10-04
from scripts import person_free as pf


def _idx(*handles):
    return pf.build_handle_index(handles)


@pytest.mark.parametrize("text", [
    "https://github.com/q7", "see github.com/q7?tab=repositories", "https://q7.github.io/site",
    "https://raw.githubusercontent.com/q7/tool/main/a.png", "github.com%2Fsynthuser%2Frepo",
])
def test_github_contexts_and_encoding_catch_handles(text):
    index = _idx("q7", "synthuser")
    hits = set(pf.handle_hits(text, index)) | set(pf.handle_hits(pf.lenient_decoded(text), index))
    assert hits & {"q7", "synthuser"}


@pytest.mark.parametrize("text", ["growth of 78% in q7 terms", "f is a letter", "github.com/some-org-name"])
def test_ordinary_text_still_clean(text):
    assert pf.handle_hits(text, _idx("78", "f")) == []


@pytest.mark.parametrize("value", ["f", "78", " F "])
def test_whole_value_equal_to_short_handle_reveals_it(value):
    assert pf.reveals_handle(value, _idx("f", "78"))


def test_homepage_checked_against_stored_and_canonical_owner():
    assert pf.safe_user_homepage("https://jd.dev", ("jd-new", "jd")) is None
    assert pf.safe_user_homepage("https://example.org", ("jd-new", "jd")) == "https://example.org"


def test_unclassified_repo_exits_4_not_a_warning(publication_repo, tmp_path, monkeypatch):
    snap_dir = tmp_path / "snaps" / "2026-10-03"
    snap_dir.mkdir(parents=True)
    (snap_dir / "snapshot.json").write_text(json.dumps({"snapshot_date": "2026-10-03", "entities": [
        {"entity_id": "e_SYNTH0000001", "name": "tool", "github_repo": "unknown-owner/tool"}]}))
    monkeypatch.setattr(hf, "SNAPSHOTS", tmp_path / "snaps")
    assert hf.main(["--date", "2026-10-03", "--dry-run"]) == 4
