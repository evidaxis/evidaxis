"""t2_deps_collect (m2): identity pinning, outage != absence, loud pin breaks.

HARD: no network. _fetch_json is the single chokepoint; tests drive it with
canned (status, body) responses keyed by URL substring. Table-driven around
the live 2026-07-02 findings: the pypi->npm identity flip, the outage recorded
forever as "no package", and total-failure-exits-green.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import t2_deps_collect as deps


def _routes(monkeypatch, table):
    """table: list of (url_substring, (status, body_dict_or_None)) checked in order."""
    def fake(url, tries=3, timeout=25):
        for frag, (st, body) in table:
            if frag in url:
                return st, (json.dumps(body).encode() if body is not None else None)
        raise AssertionError(f"unexpected URL in test: {url}")
    monkeypatch.setattr(deps, "_fetch_json", fake)


PKG_OK = {"versions": [{"versionKey": {"version": "1.0.0"}, "isDefault": True}]}
# version record with a source-repo link back to the seeded repo (identity proof)
VER_LINKED = {"links": [{"label": "SOURCE_REPO", "url": "https://github.com/a/one"}]}
DEP_OK = {"dependentCount": 7, "directDependentCount": 7, "indirectDependentCount": 0}


def _seed(tmp_path, repos, pins=None):
    (tmp_path / "etl").mkdir()
    seeds = {"verticals": {"v": {"entities": [{"github_repo": r} for r in repos]}}}
    (tmp_path / "etl" / "seeds.json").write_text(json.dumps(seeds))
    (tmp_path / "etl" / "id_map.json").write_text(
        json.dumps({r: f"e_{i:011d}" for i, r in enumerate(repos)}))
    (tmp_path / "data").mkdir()
    if pins is not None:
        (tmp_path / "data" / "deps_id_map.json").write_text(
            json.dumps({"v": "deps_pin_1", "note": "", "pins": pins}))


def test_unpinned_grid_aborts_on_error_no_cross_ecosystem_fallthrough(monkeypatch):
    # pypi probe ERRORS (outage) -> the resolver must NOT try npm and pin the
    # wrong ecosystem (the live pypi->npm flip). Today becomes fetch_error.
    _routes(monkeypatch, [("/v3/systems/pypi/", (None, None)),
                          ("/v3/systems/npm/", (200, PKG_OK))])
    out = deps.resolve_unpinned("org/mypkg")
    assert out["coverage"] == "fetch_error"


def test_unpinned_clean_404s_conclude_absence(monkeypatch):
    _routes(monkeypatch, [("/v3/systems/", (404, None))])
    assert deps.resolve_unpinned("org/mypkg")["coverage"] == "no_package_match"


def test_pinned_fetch_never_leaves_the_pinned_system(monkeypatch):
    seen = []
    def fake(url, tries=3, timeout=25):
        seen.append(url)
        if "/v3/systems/pypi/packages/mypkg" in url and ":dependents" not in url:
            return 200, json.dumps(PKG_OK).encode()
        if ":dependents" in url:
            return 200, json.dumps(DEP_OK).encode()
        raise AssertionError(f"pinned fetch escaped its pin: {url}")
    monkeypatch.setattr(deps, "_fetch_json", fake)
    out = deps.fetch_pinned({"system": "pypi", "package": "mypkg"})
    assert out["coverage"] == "matched" and out["dependent_count"] == 7
    assert all("/pypi/" in u for u in seen)


def test_pinned_404_is_pin_broken(monkeypatch):
    _routes(monkeypatch, [("/v3/systems/pypi/", (404, None))])
    assert deps.fetch_pinned({"system": "pypi", "package": "gone"})["coverage"] == "pin_broken"


def test_pinned_outage_is_fetch_error(monkeypatch):
    _routes(monkeypatch, [("/v3/systems/pypi/", (None, None))])
    assert deps.fetch_pinned({"system": "pypi", "package": "mypkg"})["coverage"] == "fetch_error"


def test_outage_day_not_written_to_history_and_run_fails(tmp_path, monkeypatch):
    _seed(tmp_path, ["a/one"], pins={"a/one": {"system": "pypi", "package": "one"}})
    monkeypatch.setattr(deps, "REPO", tmp_path)
    monkeypatch.setattr(deps, "PIN_PATH", tmp_path / "data" / "deps_id_map.json")
    _routes(monkeypatch, [("deps.dev", (None, None))])
    rc = deps.main()
    assert rc == 1, "a full outage day must fail, not land green"
    hist = list((tmp_path / "data" / "observations" / "history").glob("*.deps.jsonl"))
    assert hist == [], "an outage must never enter the long-term history as absence"
    day = next((tmp_path / "data" / "observations").glob("*/deps.jsonl"))
    rows = [json.loads(line) for line in day.read_text().splitlines()]
    assert rows[0]["coverage"] == "fetch_error"


def test_broken_pin_fails_loudly(tmp_path, monkeypatch):
    _seed(tmp_path, ["a/one"], pins={"a/one": {"system": "pypi", "package": "one"}})
    monkeypatch.setattr(deps, "REPO", tmp_path)
    monkeypatch.setattr(deps, "PIN_PATH", tmp_path / "data" / "deps_id_map.json")
    _routes(monkeypatch, [("deps.dev", (404, None))])
    assert deps.main() == 1
    day = next((tmp_path / "data" / "observations").glob("*/deps.jsonl"))
    assert json.loads(day.read_text().splitlines()[0])["coverage"] == "pin_broken"


def test_healthy_pinned_day_lands_in_history_exit_zero(tmp_path, monkeypatch):
    _seed(tmp_path, ["a/one"], pins={"a/one": {"system": "pypi", "package": "one"}})
    monkeypatch.setattr(deps, "REPO", tmp_path)
    monkeypatch.setattr(deps, "PIN_PATH", tmp_path / "data" / "deps_id_map.json")
    _routes(monkeypatch, [(":dependents", (200, DEP_OK)), ("/v3/systems/pypi/", (200, PKG_OK))])
    assert deps.main() == 0
    hist = list((tmp_path / "data" / "observations" / "history").glob("*.deps.jsonl"))
    assert len(hist) == 1
    row = json.loads(hist[0].read_text().splitlines()[0])
    assert row["coverage"] == "matched"
    assert row["signals"]["deps_dev_dependents"]["source_system"] == "pypi"


def test_new_match_gets_pinned(tmp_path, monkeypatch):
    _seed(tmp_path, ["a/one"], pins={})
    monkeypatch.setattr(deps, "REPO", tmp_path)
    monkeypatch.setattr(deps, "PIN_PATH", tmp_path / "data" / "deps_id_map.json")
    _routes(monkeypatch, [(":dependents", (200, DEP_OK)), ("/versions/", (200, VER_LINKED)),
                          ("/v3/systems/pypi/", (200, PKG_OK)), ("/v3/systems/", (404, None))])
    assert deps.main() == 0
    pins = json.loads((tmp_path / "data" / "deps_id_map.json").read_text())["pins"]
    assert pins["a/one"]["system"] == "pypi" and pins["a/one"]["package"] == "one"


def test_name_match_without_repo_linkage_is_not_identity(monkeypatch):
    """The day-1 lesson: npm `goose` (2012) is NOT block/goose. A name match whose
    version record has no link back to the system's repo must NOT match or pin."""
    stranger = {"links": [{"label": "SOURCE_REPO", "url": "https://github.com/someone/else"}]}
    _routes(monkeypatch, [(":dependents", (200, DEP_OK)), ("/versions/", (200, stranger)),
                          ("/v3/systems/pypi/", (200, PKG_OK)), ("/v3/systems/", (404, None))])
    assert deps.resolve_unpinned("a/one")["coverage"] == "no_package_match"


def test_linkage_confirmed_name_match_is_identity(monkeypatch):
    _routes(monkeypatch, [(":dependents", (200, DEP_OK)), ("/versions/", (200, VER_LINKED)),
                          ("/v3/systems/pypi/", (200, PKG_OK)), ("/v3/systems/", (404, None))])
    out = deps.resolve_unpinned("a/one")
    assert out["coverage"] == "matched" and out["newly_pinned"] is True


def test_fetch_error_rate_above_half_fails(tmp_path, monkeypatch):
    """map#4 / map#26: >50% fetch_error in one run must exit 1 (outage sensor)."""
    repos = ["a/one", "b/two", "c/three", "d/four"]
    pins = {r: {"system": "pypi", "package": r.split("/")[1]} for r in repos}
    _seed(tmp_path, repos, pins=pins)
    monkeypatch.setattr(deps, "REPO", tmp_path)
    monkeypatch.setattr(deps, "PIN_PATH", tmp_path / "data" / "deps_id_map.json")
    fail_pkgs = {"one", "two", "three"}  # 3/4 = 75% > 50%

    def majority_outage(url, tries=3, timeout=25):
        for pkg in fail_pkgs:
            if f"/packages/{pkg}" in url:
                return None, None
        if ":dependents" in url:
            return 200, json.dumps(DEP_OK).encode()
        return 200, json.dumps(PKG_OK).encode()

    monkeypatch.setattr(deps, "_fetch_json", majority_outage)
    assert deps.main() == 1


def test_one_bad_repo_fetch_error_does_not_trip_sensor(tmp_path, monkeypatch):
    """map#26: a single fetch_error among healthy pins must exit 0."""
    repos = ["a/one", "b/two", "c/three", "d/four"]
    pins = {r: {"system": "pypi", "package": r.split("/")[1]} for r in repos}
    _seed(tmp_path, repos, pins=pins)
    monkeypatch.setattr(deps, "REPO", tmp_path)
    monkeypatch.setattr(deps, "PIN_PATH", tmp_path / "data" / "deps_id_map.json")

    def one_bad(url, tries=3, timeout=25):
        if "/packages/one" in url:
            return None, None  # outage for a/one only (1/4 = 25% ≤ 50%)
        if ":dependents" in url:
            return 200, json.dumps(DEP_OK).encode()
        return 200, json.dumps(PKG_OK).encode()

    monkeypatch.setattr(deps, "_fetch_json", one_bad)
    assert deps.main() == 0
