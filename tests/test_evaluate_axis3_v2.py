"""m3-v2h evaluator: flip formula, UNEVALUABLE floor, zero-vs-absent, vote floors.

HARD: no network, no BigQuery — the evaluator is pure over observation files.
Fixtures build a tiny deps_v2 world under tmp_path.
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import evaluate_axis3_v2 as ev


def _mk_world(tmp_path, monkeypatch, rows, seeds_entities):
    obs = tmp_path / "data" / "observations" / "2026-07-16"
    obs.mkdir(parents=True)
    obs_file = obs / "deps_v2.jsonl"
    obs_file.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "etl").mkdir()
    (tmp_path / "etl" / "seeds.json").write_text(json.dumps(
        {"verticals": {"v": {"entities": seeds_entities}}}))
    (tmp_path / "etl" / "id_map.json").write_text(json.dumps(
        {e["github_repo"]: f"e_{i:03d}" for i, e in enumerate(seeds_entities)}))
    (tmp_path / "data" / "snapshots").mkdir()
    monkeypatch.setattr(ev, "REPO", tmp_path)
    monkeypatch.setattr(ev, "OBS", tmp_path / "data" / "observations")
    monkeypatch.setattr(ev, "OUT", tmp_path / "data" / "quarantine" / "eval")
    monkeypatch.setattr(ev, "FROZEN", tmp_path / "nonexistent.json")


def _row(eid, snap, value, coverage="matched"):
    sig = None if value is None else {"value": value}
    return {"entity_id": eid, "snapshot_at": snap, "coverage": coverage,
            "signals": {"deps_v2_unique_direct": sig}}


SNAPS = [f"2026-{m:02d}-01 00:00:00" for m in range(1, 15 + 1)]  # 15 monthly stand-ins


def test_zero_vs_absent_not_in_snapshot_is_never_a_point(tmp_path, monkeypatch):
    rows = [_row("e_000", SNAPS[0], 10),
            _row("e_000", SNAPS[1], None, coverage="not_in_snapshot"),
            _row("e_000", SNAPS[2], 12)]
    _mk_world(tmp_path, monkeypatch, rows, [{"github_repo": "a/one", "cohort": "c"}])
    series = ev.load_series("2026-12-31 23:59:59")
    assert [v for _, v in series["e_000"]] == [10, 12], \
        "not_in_snapshot must yield NO point, never a zero"


def test_vote_requires_min_points_and_deps_floor(tmp_path, monkeypatch):
    rows = []
    # e_000: 15 points, healthy growth, latest >= 5 -> may vote
    for i, s in enumerate(SNAPS):
        rows.append(_row("e_000", s, 10 + i * 3))
    # e_001: only 5 points -> below MIN_POINTS, never eligible
    for s in SNAPS[:5]:
        rows.append(_row("e_001", s, 100))
    # e_002: 15 points but latest below DEPS_FLOOR -> never eligible
    for s in SNAPS:
        rows.append(_row("e_002", s, 2))
    seeds = [{"github_repo": "a/one", "cohort": "c"},
             {"github_repo": "a/two", "cohort": "c"},
             {"github_repo": "a/three", "cohort": "c"}]
    _mk_world(tmp_path, monkeypatch, rows, seeds)
    series = ev.load_series("2026-12-31 23:59:59")
    eligible, rising, per = ev.votes_at_cutoff(series, {"e_000": "c", "e_001": "c", "e_002": "c"},
                                               "2026-12-31 23:59:59")
    assert "e_001" not in eligible, "below MIN_POINTS must not vote"
    assert "e_002" not in eligible, "below DEPS_FLOOR must not vote"


def test_flip_formula_symmetric_difference_over_union():
    # Direct check of the arithmetic used in evaluate(): R changes by 1 of 5
    Ea, Ra = {"a", "b", "c", "d", "e"}, {"a", "b"}
    Eb, Rb = {"a", "b", "c", "d", "e"}, {"a", "c"}
    flip = len(Ra ^ Rb) / len(Ea | Eb)
    assert flip == 2 / 5  # b left, c entered -> symmetric difference = 2


def test_flip_transition_unevaluable_below_denominator_floor(tmp_path, monkeypatch):
    # Two entities only -> |E_a U E_b| = 2 < MIN_FLIP_DENOM -> UNEVALUABLE, not PASS
    rows = []
    for i, s in enumerate(SNAPS):
        rows.append(_row("e_000", s, 10 + i))
        rows.append(_row("e_001", s, 20 + i))
    seeds = [{"github_repo": "a/one", "cohort": "c"},
             {"github_repo": "a/two", "cohort": "c"}]
    _mk_world(tmp_path, monkeypatch, rows, seeds)
    result = ev.evaluate("2026-12-31 23:59:59", "baseline")
    t = result["criteria"]["c3_flip"]["transitions"]
    assert t, "transitions must exist for 15 snapshots"
    assert all(x.get("status") == "UNEVALUABLE" for x in t), \
        "denominator below floor must be UNEVALUABLE"
    assert result["criteria"]["c3_flip"]["pass"] is False, \
        "all-UNEVALUABLE must not auto-PASS the flip criterion"


def test_as_of_excludes_future_snapshots(tmp_path, monkeypatch):
    rows = [_row("e_000", SNAPS[0], 10), _row("e_000", SNAPS[14], 99)]
    _mk_world(tmp_path, monkeypatch, rows, [{"github_repo": "a/one", "cohort": "c"}])
    series = ev.load_series(SNAPS[5])
    assert [v for _, v in series["e_000"]] == [10], "points after --as-of must be excluded"
