"""End-to-end collector pipeline test for etl/collect.py.

This is the highest-value test: it drives collect.main() over a SMALL, fully
controlled seeds + fully faked GitHub/OpenAlex responses (NO network — _get_json
is monkeypatched) and asserts the whole locked methodology end to end:

  * the four engineered display statuses (rising / watch / calibration / tracked),
  * the convergence gate (>=2 axes present AND >=2 axes rising; incumbent forced
    out of "rising"),
  * every emitted P5 artifact (snapshot bundle + SHA256SUMS, manifest, provenance,
    latest pointer, taxonomy nodes, redirects, header-only relationships table,
    id_map, per-entity dossier cards + append-only history JSONL),
  * SHA256SUMS == recomputed sha256 of the actual file bytes,
  * reproducibility: snapshot_id + manifest_hash are stable across two runs even
    though snapshot.json bytes differ (captured_at is timestamped).

The seeds are engineered (see ENGINEERED_* below) so the cohort z-scores land on
known signs: stars are FLAT across the cohort, which neutralizes the axis-1
size-residualize (robust_z of equal sizes is all-zero -> beta 0 -> residual == z),
giving deterministic rising/not-rising verdicts.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date

import pytest

import collect


# ----------------------------------------------------------------- engineered fixtures

# One vertical, four entities. Flat stars (size proxy) neutralize the axis-1
# residualize; varied axis-2 totals exercise the axis-2 residualize.
CY = date.today().year  # collect uses date.today().year as the "current year"


def _weekly(base, growth, n=30):
    """30 weeks of commit_activity totals on a straight line (>=26 for axis-1)."""
    return [max(0, round(base + growth * i)) for i in range(n)]


# m2 gate (z>=1 + cohort_size>=5): a 5-entity cohort with EXTREME axis-1 separation so the two
# positive-slope outliers (rise, watch) clamp well above the z>=1 rising floor and the three
# decliners sit clearly below. (Flat stars neutralize the axis-1 size-residualize.)
WEEKLY = {
    "acme/rise": _weekly(1, 4.0),    # extreme up -> axis1 z clamps high (>=1) -> axis1 rising
    "acme/watch": _weekly(2, 3.0),   # extreme up -> axis1 z >= 1               -> axis1 rising
    "acme/inc": _weekly(40, -0.6),   # declining  -> axis1 z < 0                -> not rising
    "acme/track": _weekly(35, -1.0),  # declining  -> axis1 z < 0                -> not rising
    "acme/ctx": _weekly(30, -0.8),   # declining  -> axis1 z < 0  (cohort padder to n=5)
}

# axis-2 OpenAlex citation series. current year (CY) is PARTIAL -> dropped; 5 completed years
# -> earliest (birth) dropped, fit on 4. Totals kept SIMILAR across the cohort so the axis-2
# size-residualize is ~no-op; only RISE accelerates (the lone axis-2 riser).
CITES = {
    "W_RISE": {CY - 5: 5, CY - 4: 12, CY - 3: 28, CY - 2: 55, CY - 1: 110, CY: 40},   # accelerating -> axis2 rising
    "W_WATCH": {CY - 5: 95, CY - 4: 72, CY - 3: 50, CY - 2: 32, CY - 1: 16, CY: 5},   # declining
    "W_INC": {CY - 5: 45, CY - 4: 46, CY - 3: 44, CY - 2: 45, CY - 1: 44, CY: 10},    # flat
    "W_TRACK": {CY - 5: 90, CY - 4: 68, CY - 3: 46, CY - 2: 30, CY - 1: 15, CY: 4},   # declining
    "W_CTX": {CY - 5: 85, CY - 4: 64, CY - 3: 44, CY - 2: 30, CY - 1: 16, CY: 6},     # declining
}

# Expected per-repo: (display name, work-id list, incumbent?, expected status, expected rising?)
EXPECT = {
    "acme/rise": ("RiseBot", ["W_RISE"], False, "rising", True),
    "acme/watch": ("Watch Tower", ["W_WATCH"], False, "watch", False),
    "acme/inc": ("Inc Engine", ["W_INC"], True, "calibration", False),
    "acme/track": ("TrackLab", ["W_TRACK"], False, "tracked", False),
    "acme/ctx": ("Context Pad", ["W_CTX"], False, "tracked", False),
}

FLAT_STARS = 1000  # identical across the cohort -> axis-1 residualize is a no-op


def _small_seeds():
    """seeds.json schema mirrors the real one: domain + verticals{label,industry_slug,
    subniche_slug, entities[]}; each entity has github_repo + name (+ optional
    openalex_work_ids / incumbent)."""
    return {
        "meta": {"version": "test", "note": "engineered cohort for the pipeline test"},
        "domain": {"slug": "ai", "label": "Artificial Intelligence"},
        "verticals": {
            "test-cohort": {
                "label": "Test Cohort — Engineered",
                "industry_slug": "test-industry",
                "subniche_slug": "test-subniche",
                "entities": [
                    {
                        "github_repo": repo,
                        "entity_type": "repo",
                        "name": name,
                        "homepage": f"https://example.com/{name}",
                        "openalex_work_ids": works,
                        **({"incumbent": True} if inc else {}),
                    }
                    for repo, (name, works, inc, _st, _ri) in EXPECT.items()
                ],
            }
        },
    }


def _fake_get_json(url, headers=None, tries=5):
    """Deterministic, network-free _get_json. Dispatches on the URL:
      * /repos/<owner>/<repo>            -> repo meta (stars FLAT, created_at)
      * /repos/<owner>/<repo>/stats/...  -> commit_activity list (30 weekly totals)
      * api.openalex.org/works/<wid>     -> one OpenAlex work (counts_by_year)
    """
    # --- OpenAlex ---
    m = re.search(r"openalex\.org/works/([^?]+)", url)
    if m:
        wid = m.group(1)
        counts = CITES[wid]
        return {
            "id": f"https://openalex.org/{wid}",
            "display_name": f"paper-{wid}",
            "cited_by_count": sum(counts.values()),
            "counts_by_year": [
                {"year": y, "cited_by_count": c} for y, c in sorted(counts.items())
            ],
        }
    # --- GitHub commit activity (check BEFORE the bare /repos/ branch) ---
    m = re.search(r"/repos/([^/]+/[^/]+)/stats/commit_activity", url)
    if m:
        repo = m.group(1)
        return [{"total": t} for t in WEEKLY[repo]]
    # --- GitHub repo meta ---
    m = re.search(r"/repos/([^/]+/[^/]+)$", url)
    if m:
        repo = m.group(1)
        return {"stargazers_count": FLAT_STARS, "created_at": "2021-01-01T00:00:00Z",
                "full_name": repo}
    raise AssertionError(f"unexpected URL hit the faked _get_json: {url!r}")


@pytest.fixture
def run_pipeline(isolated_repo, monkeypatch):
    """isolated_repo redirects collect.ROOT/REPO to a tmp tree. Overwrite the seeded
    seeds.json with our small engineered one, install the network-free _get_json, and
    return a callable that runs collect.main() and yields the tmp repo root."""
    (collect.ROOT / "seeds.json").write_text(json.dumps(_small_seeds()))
    monkeypatch.setattr(collect, "_get_json", _fake_get_json, raising=True)

    def _run():
        collect.main()
        return isolated_repo  # tmp repo root (== collect.REPO)

    return _run


def _load_snapshot(repo_root):
    dstr = date.today().isoformat()
    snap = repo_root / "data" / "snapshots" / dstr / "snapshot.json"
    return json.loads(snap.read_text()), snap.parent


def _by_repo(snapshot):
    return {e["github_repo"]: e for e in snapshot["entities"]}


# ----------------------------------------------------------------- tests


def test_snapshot_written_and_entity_count(run_pipeline):
    repo = run_pipeline()
    snapshot, snap_dir = _load_snapshot(repo)
    assert snap_dir.exists()
    assert snapshot["counts"]["entities"] == len(EXPECT) == 5
    assert len(snapshot["entities"]) == 5
    # static header fields are emitted
    assert snapshot["schema_version"] == collect.SCHEMA_VER
    assert snapshot["methodology_version"] == collect.METHODOLOGY_VERSION
    assert snapshot["license"] == "CC0-1.0"
    assert snapshot["snapshot_date"] == date.today().isoformat()


@pytest.mark.parametrize("repo", list(EXPECT.keys()))
def test_engineered_statuses(run_pipeline, repo):
    """Each entity lands on its engineered display status + rising flag."""
    snap, _ = _load_snapshot(run_pipeline())
    e = _by_repo(snap)[repo]
    _name, _works, _inc, want_status, want_rising = EXPECT[repo]
    assert e["status"] == want_status, (repo, e["status"], e.get("convergent_axes"))
    assert e["rising"] is want_rising


def test_incumbent_is_calibration_not_rising(run_pipeline):
    """The incumbent entity is measured (2 axes present) but forced to 'calibration'
    and rising=False even though its axis-2 alone reads rising."""
    snap, _ = _load_snapshot(run_pipeline())
    inc = _by_repo(snap)["acme/inc"]
    assert inc["incumbent"] is True
    assert inc["status"] == "calibration"
    assert inc["rising"] is False
    assert len(inc["axes_present"]) >= 2  # it IS measured on both axes


def test_convergence_gate_counts(run_pipeline):
    """The cohort counts reflect the gate: exactly one rising, one watch, one
    calibration, one tracked; and all four resolved axis-2 to 'present'."""
    snap, _ = _load_snapshot(run_pipeline())
    c = snap["counts"]
    assert c["rising"] == 1
    assert c["watch"] == 1
    assert c["calibration"] == 1
    assert c["tracked"] == 2
    assert c["axis2_present"] == 5
    # rising entity has 2 convergent axes; watch has exactly 1
    by = _by_repo(snap)
    assert len(by["acme/rise"]["convergent_axes"]) == 2
    assert len(by["acme/watch"]["convergent_axes"]) == 1
    assert len(by["acme/track"]["convergent_axes"]) == 0


def test_momentum_and_percentile_bounds(run_pipeline):
    """momentum is in [0,100] (or None for unscored); every scored entity has a
    percentile, and the cohort percentile range spans 0..100 here."""
    snap, _ = _load_snapshot(run_pipeline())
    pcts = []
    for e in snap["entities"]:
        m = e["momentum"]
        assert m is None or (0.0 <= m <= 100.0), m
        if m is not None:
            assert e["percentile"] is not None
            pcts.append(e["percentile"])
    # all five are scored on >=1 axis here
    assert len(pcts) == 5
    assert min(pcts) == 0 and max(pcts) == 100
    # the rising entity sits at the top of the cohort by momentum
    by = _by_repo(snap)
    assert by["acme/rise"]["momentum"] == max(e["momentum"] for e in snap["entities"])


def test_sha256sums_match_file_bytes(run_pipeline):
    """SHA256SUMS lists snapshot/manifest/provenance and each hash equals the
    recomputed sha256 of that file's actual bytes."""
    repo = run_pipeline()
    _snap, snap_dir = _load_snapshot(repo)
    text = (snap_dir / "SHA256SUMS").read_text()
    listed = {}
    for line in text.strip().splitlines():
        h, fn = line.split("  ", 1)
        listed[fn] = h
    assert set(listed) == {"snapshot.json", "manifest.json", "provenance.json"}
    for fn, h in listed.items():
        recomputed = hashlib.sha256((snap_dir / fn).read_bytes()).hexdigest()
        assert recomputed == h, fn


def test_all_artifacts_written(run_pipeline):
    """Every P5 artifact lands on disk in the right place."""
    repo = run_pipeline()
    dstr = date.today().isoformat()
    snap_dir = repo / "data" / "snapshots" / dstr
    for fn in ("snapshot.json", "manifest.json", "provenance.json", "SHA256SUMS"):
        assert (snap_dir / fn).exists(), fn
    assert (repo / "data" / "latest.json").exists()
    assert (repo / "taxonomy" / "nodes.json").exists()
    assert (repo / "redirects.yaml").exists()
    assert (repo / "relationships.tsv").exists()
    assert (repo / "etl" / "id_map.json").exists()

    # latest.json points at this snapshot
    latest = json.loads((repo / "data" / "latest.json").read_text())
    manifest = json.loads((snap_dir / "manifest.json").read_text())
    prov = json.loads((snap_dir / "provenance.json").read_text())
    assert latest["snapshot_date"] == dstr
    assert latest["snapshot_id"] == manifest["snapshot_id"] == prov["snapshot_id"]
    assert manifest["manifest_hash"] == prov["manifest_hash"]


def test_relationships_table_header_only(run_pipeline):
    """The reserved relationships table is created header-only: exactly one line."""
    repo = run_pipeline()
    text = (repo / "relationships.tsv").read_text()
    lines = text.splitlines()
    assert len(lines) == 1
    assert lines[0].split("\t")[0] == "rel_id"
    assert "rel_type" in lines[0]


def test_redirects_yaml_content(run_pipeline):
    repo = run_pipeline()
    text = (repo / "redirects.yaml").read_text()
    assert "rules:" in text
    assert "/e/:entity_id/:slug" in text
    assert "/e/:entity_id" in text


def test_taxonomy_nodes(run_pipeline):
    """Taxonomy registry: 1 domain + (industry+sub_niche) per vertical = 3 nodes."""
    repo = run_pipeline()
    tax = json.loads((repo / "taxonomy" / "nodes.json").read_text())
    assert tax["taxonomy_version"] == "tax_1"
    levels = sorted(n["level"] for n in tax["nodes"])
    assert levels == ["domain", "industry", "sub_niche"]
    dom = next(n for n in tax["nodes"] if n["level"] == "domain")
    assert dom["slug"] == "ai" and dom["parent"] is None
    ind = next(n for n in tax["nodes"] if n["level"] == "industry")
    assert ind["parent"] == "ai"


def test_id_map_is_deterministic_minting(run_pipeline):
    """etl/id_map.json maps each seeded repo -> its minted id, and the id equals
    mint_entity_id(repo) (pure function of the natural key)."""
    repo = run_pipeline()
    id_map = json.loads((repo / "etl" / "id_map.json").read_text())
    assert set(id_map) == set(EXPECT)
    for r, eid in id_map.items():
        assert eid == collect.mint_entity_id(r)
        assert re.fullmatch(r"e_[0-9A-HJKMNP-TV-Z]{11}", eid), eid  # Crockford, 10+chk


def test_entity_cards_and_history(run_pipeline):
    """Each entity gets a dossier card with YAML frontmatter (entity_id + score
    block) and a one-liner body, and one history JSONL line is appended."""
    repo = run_pipeline()
    snap, _ = _load_snapshot(repo)
    for e in snap["entities"]:
        eid = e["entity_id"]
        card = repo / "entities" / f"{eid}.md"
        assert card.exists(), eid
        text = card.read_text()
        # frontmatter
        assert text.startswith("---\n")
        assert text.count("---") >= 2
        assert f"entity_id: {eid}" in text
        assert "score:" in text          # the DERIVED score block
        assert f"status: {e['status']}" in text
        assert f"snapshot_id: {snap['snapshot_id']}" in text
        # body one-liner mentions the entity and the heading
        assert f"# {e['name']}" in text
        assert "Evidaxis" in text.split("---", 2)[-1]

        # history JSONL appended with exactly one line on a single run
        hist = repo / "data" / "history" / f"{eid}.jsonl"
        assert hist.exists()
        hlines = hist.read_text().splitlines()
        assert len(hlines) == 1
        row = json.loads(hlines[0])
        assert row["entity_id"] == eid
        assert row["snapshot_id"] == snap["snapshot_id"]
        assert row["rising"] is e["rising"]


def test_rising_card_one_liner(run_pipeline):
    """The rising entity's body one-liner reflects 'rising' + the converging-axes
    count; the tracked-only entity's does not claim rising."""
    repo = run_pipeline()
    snap, _ = _load_snapshot(repo)
    by = _by_repo(snap)
    rise_card = (repo / "entities" / f"{by['acme/rise']['entity_id']}.md").read_text()
    assert "**rising**" in rise_card
    assert "independent axes converging" in rise_card


def test_reproducibility_two_runs(run_pipeline):
    """Run the pipeline twice with identical fakes. snapshot_id and manifest_hash
    (the score-defining identity) are IDENTICAL across runs even though snapshot.json
    bytes need not be (captured_at is a wall-clock timestamp)."""
    repo = run_pipeline()
    snap1, _ = _load_snapshot(repo)
    prov1 = json.loads((repo / "data" / "snapshots" / date.today().isoformat()
                        / "provenance.json").read_text())

    # second run (same seeds, same fakes) overwrites the same day's snapshot dir
    collect.main()
    snap2, _ = _load_snapshot(repo)
    prov2 = json.loads((repo / "data" / "snapshots" / date.today().isoformat()
                        / "provenance.json").read_text())

    # the reproducible identity is stable
    assert snap1["snapshot_id"] == snap2["snapshot_id"]
    assert prov1["manifest_hash"] == prov2["manifest_hash"]
    assert prov1["snapshot_id"] == snap1["snapshot_id"]

    # captured_at MAY differ (timestamped); if the two runs land in the same wall
    # second it can match. Either way snapshot_id must be stable — already asserted.
    if snap1["captured_at"] != snap2["captured_at"]:
        # documents that bytes differ while the score identity does not
        assert snap1["snapshot_id"] == snap2["snapshot_id"]


# ----------------------------------------------------------------- secondary pipeline variant
# A second engineered cohort that exercises the axis-2 absent/insufficient branches,
# the 'single-axis' display status, the no-data (404) skip, and the corresponding
# dossier one-liners — paths the four-entity rising/watch/calibration/tracked cohort
# above does not reach.

WEEKLY2 = {
    # two CLOSE decliners (small spread -> tiny MAD) + one lone steep riser, so the riser's
    # within-cohort z clamps to +3 (>= the m2 z>=1 floor) -> axis1 rising -> 'watch'.
    "x/single": _weekly(20, -1.0),   # declining -> axis1 NOT rising -> single-axis (axis2 absent)
    "x/absent": _weekly(20, -0.95),  # declining (close to single) -> NOT the rising outlier
    "x/insuff": _weekly(1, 10.0),    # lone steep riser -> axis1 z clamps high (>=1) -> axis1 rising -> watch
    # "x/nodata" deliberately returns None from the faked _get_json (404 -> skipped)
}
# x/insuff has an OpenAlex work with only 2 completed years -> axis-2 'insufficient'.
CITES2 = {
    "W_INSUFF": {CY - 2: 3, CY - 1: 8, CY: 2},
}


def _seeds2():
    ents = [
        {"github_repo": "x/single", "entity_type": "repo", "name": "Single Axis",
         "homepage": "https://example.com/single", "openalex_work_ids": []},
        {"github_repo": "x/insuff", "entity_type": "repo", "name": "Insufficient",
         "homepage": "https://example.com/insuff", "openalex_work_ids": ["W_INSUFF"]},
        {"github_repo": "x/absent", "entity_type": "repo", "name": "No Paper",
         "homepage": "https://example.com/absent", "openalex_work_ids": []},
        {"github_repo": "x/nodata", "entity_type": "repo", "name": "Gone",
         "homepage": "https://example.com/nodata", "openalex_work_ids": []},
    ]
    return {
        "meta": {"version": "test2"},
        "domain": {"slug": "ai", "label": "Artificial Intelligence"},
        "verticals": {
            "branch-cohort": {
                "label": "Branch Cohort",
                "industry_slug": "branch-industry",
                "subniche_slug": "branch-subniche",
                "entities": ents,
            }
        },
    }


def _fake_get_json2(url, headers=None, tries=5):
    m = re.search(r"openalex\.org/works/([^?]+)", url)
    if m:
        wid = m.group(1)
        counts = CITES2[wid]
        return {"id": f"https://openalex.org/{wid}", "display_name": f"paper-{wid}",
                "cited_by_count": sum(counts.values()),
                "counts_by_year": [{"year": y, "cited_by_count": c}
                                   for y, c in sorted(counts.items())]}
    m = re.search(r"/repos/([^/]+/[^/]+)/stats/commit_activity", url)
    if m:
        repo = m.group(1)
        if repo == "x/nodata":
            return None  # 404 -> "no data" -> entity skipped
        return [{"total": t} for t in WEEKLY2[repo]]
    m = re.search(r"/repos/([^/]+/[^/]+)$", url)
    if m:
        repo = m.group(1)
        if repo == "x/nodata":
            return None
        return {"stargazers_count": FLAT_STARS, "created_at": "2022-06-01T00:00:00Z"}
    raise AssertionError(f"unexpected URL: {url!r}")


@pytest.fixture
def run_pipeline2(isolated_repo, monkeypatch):
    (collect.ROOT / "seeds.json").write_text(json.dumps(_seeds2()))
    monkeypatch.setattr(collect, "_get_json", _fake_get_json2, raising=True)

    def _run():
        collect.main()
        return isolated_repo

    return _run


def test_branch_cohort_statuses_and_skip(run_pipeline2):
    """The no-data repo is skipped; the survivors land on single-axis / watch; the
    insufficient-axis-2 entity is measured on one axis only."""
    repo = run_pipeline2()
    snap, _ = _load_snapshot(repo)
    by = _by_repo(snap)
    # x/nodata never made it into the snapshot (404 on meta+stats -> continue)
    assert "x/nodata" not in by
    assert snap["counts"]["entities"] == 3

    # x/single: 1 axis present, 0 rising -> 'single-axis'; axis-2 'absent'
    single = by["x/single"]
    assert single["status"] == "single-axis"
    assert single["rising"] is False
    assert single["axes"]["openalex_citation_momentum"]["status"] == "absent"

    # x/insuff: axis-2 'insufficient' (only 2 completed years), axis-1 rising -> 'watch'
    insuff = by["x/insuff"]
    assert insuff["axes"]["openalex_citation_momentum"]["status"] == "insufficient"
    assert insuff["status"] == "watch"  # 1 axis present & rising

    # x/absent: axis-2 'absent', axis-1 rising -> 'watch'
    assert by["x/absent"]["axes"]["openalex_citation_momentum"]["status"] == "absent"


def test_branch_cohort_one_liners(run_pipeline2):
    """The 'absent' and 'insufficient' axis-2 dossiers render their distinct
    one-liners (development-velocity-only / too-young-citation-history)."""
    repo = run_pipeline2()
    snap, _ = _load_snapshot(repo)
    by = _by_repo(snap)
    single_card = (repo / "entities" / f"{by['x/single']['entity_id']}.md").read_text()
    assert "development-velocity only" in single_card  # axis-2 absent branch
    insuff_card = (repo / "entities" / f"{by['x/insuff']['entity_id']}.md").read_text()
    assert "too young" in insuff_card                  # axis-2 insufficient branch


# ----------------------------------------------------------------- pure-function units


@pytest.mark.parametrize("key,expected", [
    ("huggingface/lerobot", "e_"),  # only the prefix/shape is asserted below
])
def test_mint_entity_id_shape_and_determinism(key, expected):
    a = collect.mint_entity_id(key)
    b = collect.mint_entity_id(key)
    assert a == b                                  # pure function -> stable
    assert a.startswith(expected)
    assert re.fullmatch(r"e_[0-9A-HJKMNP-TV-Z]{11}", a)  # Crockford32, no I L O U
    # case-insensitive on the natural key
    assert collect.mint_entity_id(key.upper()) == a


@pytest.mark.parametrize("name,slug", [
    ("LeRobot", "lerobot"),
    ("Isaac Lab", "isaac-lab"),
    ("ESM / ESMFold", "esm-esmfold"),
    ("!!!", "x"),                # all-symbol -> fallback 'x'
    ("a--b__c", "a-b-c"),
])
def test_slugify(name, slug):
    assert collect.slugify(name) == slug


@pytest.mark.parametrize("ys,expect_none", [
    ([1, 2], True),     # n < 3 -> None
    ([1, 1, 1], False),
])
def test_log_slope_short_series(ys, expect_none):
    out = collect.log_slope(ys)
    assert (out is None) is expect_none


def test_log_slope_monotone_signs():
    """Rising series -> positive slope; falling -> negative; flat -> ~0."""
    assert collect.log_slope([1, 2, 4, 8, 16]) > 0
    assert collect.log_slope([16, 8, 4, 2, 1]) < 0
    assert abs(collect.log_slope([5, 5, 5, 5])) < 1e-9


def test_robust_z_centers_on_median():
    """median maps to ~0; a single giant is winsorized to +3 (not unbounded)."""
    z = collect.robust_z([1, 2, 3, 4, 1000])
    assert abs(z[2]) < 1e-6           # the median element
    assert max(z) <= 3.0 and min(z) >= -3.0
    assert z[-1] == 3.0               # the giant is clamped


def test_residualize_noop_on_tiny_cohort():
    """n < 4 returns the z-scores unchanged (guard for tiny cohorts)."""
    zs = [0.5, -0.5, 1.0]
    assert collect.residualize(zs, [10, 20, 30]) == zs


def test_residualize_noop_on_flat_size():
    """Equal sizes -> size-axis variance ~0 -> beta 0 -> residual == input z."""
    zs = [1.0, -1.0, 0.5, -0.5]
    out = collect.residualize(zs, [100, 100, 100, 100])
    assert out == pytest.approx(zs)


@pytest.mark.parametrize("work_ids,expect_status", [
    ([], "absent"),                                  # no work ids -> structurally absent
])
def test_axis2_slope_no_works(work_ids, expect_status):
    status, slope, total, detail = collect.axis2_slope(work_ids, CY)
    assert status == expect_status
    assert slope is None and total == 0 and detail == {}


def test_axis2_slope_present_drops_birth_year(monkeypatch):
    """>=4 completed years -> earliest (birth) year dropped; partial current year
    dropped; needs >=3 completed to vote -> 'present'."""
    counts = {CY - 5: 1, CY - 4: 10, CY - 3: 25, CY - 2: 50, CY - 1: 90, CY: 30}
    monkeypatch.setattr(collect, "_get_json", lambda url, *a, **k: {
        "id": "W", "display_name": "t", "cited_by_count": sum(counts.values()),
        "counts_by_year": [{"year": y, "cited_by_count": c} for y, c in counts.items()],
    }, raising=True)
    status, slope, total, detail = collect.axis2_slope(["W"], CY)
    assert status == "present"
    assert slope is not None and slope > 0           # accelerating
    assert total == sum(counts.values())             # includes the partial year in total
    assert detail["by_year"][CY] == 30


def test_axis2_slope_insufficient(monkeypatch):
    """Only 2 completed years -> 'insufficient' (cannot vote)."""
    counts = {CY - 2: 3, CY - 1: 8, CY: 2}
    monkeypatch.setattr(collect, "_get_json", lambda url, *a, **k: {
        "id": "W", "display_name": "t", "cited_by_count": 13,
        "counts_by_year": [{"year": y, "cited_by_count": c} for y, c in counts.items()],
    }, raising=True)
    status, slope, total, _ = collect.axis2_slope(["W"], CY)
    assert status == "insufficient"
    assert slope is None and total == 13


def test_axis2_slope_empty_response_absent(monkeypatch):
    """A work that yields no counts_by_year (or a RATELIMIT sentinel) -> absent."""
    monkeypatch.setattr(collect, "_get_json", lambda url, *a, **k: "RATELIMIT",
                        raising=True)
    status, slope, total, detail = collect.axis2_slope(["W"], CY)
    assert status == "absent"
    assert slope is None and total == 0 and detail == {}


def test_iso_period_format():
    p = collect.iso_period(date(2026, 6, 30))
    assert re.fullmatch(r"\d{4}-w\d{2}", p)
    assert p == "2026-w27"


def test_yaml_escape():
    assert collect._yaml_escape(None) == '""'
    assert collect._yaml_escape('he said "hi"') == '"he said \\"hi\\""'
    assert collect._yaml_escape("plain") == '"plain"'


def test_load_github_token_from_env_file(tmp_path, monkeypatch):
    """_load_github_token reads GITHUB_TOKEN= from etl/.env when the env var is unset."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("EVIDAXIS_GITHUB_ENV", raising=False)
    fake_etl = tmp_path / "etl"
    fake_etl.mkdir()
    (fake_etl / ".env").write_text('GITHUB_TOKEN="ghp_secret123"\n')
    monkeypatch.setattr(collect, "ROOT", fake_etl, raising=True)
    assert collect._load_github_token() == "ghp_secret123"


def test_load_github_token_prefers_env_var(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "  from_env  ")
    assert collect._load_github_token() == "from_env"


def test_load_seeds_reads_root(isolated_repo):
    """load_seeds() reads collect.ROOT/seeds.json (the isolated_repo seeds copy)."""
    (collect.ROOT / "seeds.json").write_text(json.dumps(_small_seeds()))
    seeds = collect.load_seeds()
    assert seeds["domain"]["slug"] == "ai"
    assert "test-cohort" in seeds["verticals"]


def test_main_aborts_on_github_ratelimit(isolated_repo, monkeypatch, capsys):
    """If GitHub returns the RATELIMIT sentinel, main() prints ABORT and returns
    WITHOUT writing a snapshot (no partial artifacts)."""
    (collect.ROOT / "seeds.json").write_text(json.dumps(_small_seeds()))
    monkeypatch.setattr(collect, "_get_json", lambda url, *a, **k: "RATELIMIT",
                        raising=True)
    collect.main()
    out = capsys.readouterr().out
    assert "ABORT" in out
    assert not (isolated_repo / "data" / "snapshots" / date.today().isoformat()).exists()


def test_two_present_axis2_not_z_scored(isolated_repo, monkeypatch):
    """With exactly 2 axis-2-present entities (too few to robust-z), axis2_z is set
    to None and axis-2 cannot vote; both end up not-rising (only axis-1 can rise).
    Covers the `elif len(a2_rows) >= 2` branch."""
    # 3-entity cohort so axis-1 z is computed; only 2 of them carry an OpenAlex work.
    seeds = {
        "meta": {"version": "t3"},
        "domain": {"slug": "ai", "label": "Artificial Intelligence"},
        "verticals": {"c": {
            "label": "C", "industry_slug": "i", "subniche_slug": "s",
            "entities": [
                {"github_repo": "p/a", "entity_type": "repo", "name": "A",
                 "homepage": "h", "openalex_work_ids": ["W_RISE"]},
                {"github_repo": "p/b", "entity_type": "repo", "name": "B",
                 "homepage": "h", "openalex_work_ids": ["W_INC"]},
                {"github_repo": "p/c", "entity_type": "repo", "name": "C",
                 "homepage": "h", "openalex_work_ids": []},
            ],
        }},
    }
    (collect.ROOT / "seeds.json").write_text(json.dumps(seeds))
    weeklies = {"p/a": _weekly(2, 1.0), "p/b": _weekly(5, 0.6), "p/c": _weekly(8, -0.5)}

    def fake(url, headers=None, tries=5):
        m = re.search(r"openalex\.org/works/([^?]+)", url)
        if m:
            counts = CITES[m.group(1)]
            return {"id": "W", "display_name": "t", "cited_by_count": sum(counts.values()),
                    "counts_by_year": [{"year": y, "cited_by_count": c}
                                       for y, c in sorted(counts.items())]}
        m = re.search(r"/repos/([^/]+/[^/]+)/stats/commit_activity", url)
        if m:
            return [{"total": t} for t in weeklies[m.group(1)]]
        m = re.search(r"/repos/([^/]+/[^/]+)$", url)
        if m:
            return {"stargazers_count": FLAT_STARS, "created_at": "2021-01-01T00:00:00Z"}
        raise AssertionError(url)

    monkeypatch.setattr(collect, "_get_json", fake, raising=True)
    collect.main()
    snap, _ = _load_snapshot(isolated_repo)
    by = _by_repo(snap)
    # both axis-2-present entities have a null cohort_z (not z-scored) -> cannot vote
    assert by["p/a"]["axes"]["openalex_citation_momentum"]["status"] == "present"
    assert by["p/a"]["axes"]["openalex_citation_momentum"]["cohort_z"] is None
    assert by["p/b"]["axes"]["openalex_citation_momentum"]["cohort_z"] is None
    # axis-2 cannot lift anyone to 'rising' (needs 2 voting axes); none are rising
    assert snap["counts"]["rising"] == 0


def test_card_carries_note_field(isolated_repo, monkeypatch):
    """An entity seeded with a 'note' renders that note into its dossier frontmatter
    (covers the optional-note branch of the card writer)."""
    seeds = _small_seeds()
    # add a note to the first entity
    seeds["verticals"]["test-cohort"]["entities"][0]["note"] = "engineered note line"
    (collect.ROOT / "seeds.json").write_text(json.dumps(seeds))
    monkeypatch.setattr(collect, "_get_json", _fake_get_json, raising=True)
    collect.main()
    snap, _ = _load_snapshot(isolated_repo)
    rise = _by_repo(snap)["acme/rise"]
    card = (isolated_repo / "entities" / f"{rise['entity_id']}.md").read_text()
    assert "note:" in card
    assert "engineered note line" in card
