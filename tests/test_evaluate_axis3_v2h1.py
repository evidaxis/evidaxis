"""Tests for the v2h.1 evaluator's council mechanics: state machine (clean
prefix only, provisional never load-bearing), verdict-layer canary, one-way
fragility veto. Uses the pure scoring/canary primitives directly."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collectors"))

from evaluate_axis3_v2h1 import (
    CANARY_AGREEMENT_FLOOR,
    MIN_POINTS,
    _ols_slope,
    _theil_sen_slope,
    canary,
    votes_at_cutoff,
)


def _mk_series(vals_by_entity, snaps):
    return {eid: [(s, v) for s, v in zip(snaps, vals, strict=True)]
            for eid, vals in vals_by_entity.items()}


SNAPS = [f"2026-02-{d:02d}" for d in range(1, MIN_POINTS + 2)]  # 15 snapshots


def test_votes_use_only_allowed_snapshots():
    # entity rises strongly on clean data; a corrupt snapshot (huge dip) is
    # excluded via the allowed list -> the dip must not affect the vote
    dirty = SNAPS[7]
    vals = [100 + 10 * i for i in range(len(SNAPS))]
    vals[7] = 1  # corrupt point
    series = _mk_series({f"e{i}": vals for i in range(6)}, SNAPS)
    cohorts = {f"e{i}": "c" for i in range(6)}
    clean = [s for s in SNAPS if s != dirty]
    E, _R, per = votes_at_cutoff(series, cohorts, clean)
    assert len(E) == 6
    # slopes computed without the corrupt point are positive for everyone
    assert all(v["slope"] > 0 for v in per.values())


def test_min_points_enforced_on_clean_prefix():
    # 15 snapshots but only 13 clean -> below MIN_POINTS -> nobody votes
    clean = SNAPS[:MIN_POINTS - 1]
    series = _mk_series({f"e{i}": [100 + i * j for j in range(len(SNAPS))]
                         for i in range(6)}, SNAPS)
    cohorts = {f"e{i}": "c" for i in range(6)}
    E, R, _per = votes_at_cutoff(series, cohorts, clean)
    assert E == set() and R == set()


def test_one_way_veto_withholds_fragile_vote():
    # an entity whose positive OLS slope exists only because of the last point
    # (LOO flip) must be vetoed from rising — but the veto never grants a vote
    flat_then_jump = [100] * (len(SNAPS) - 1) + [140]
    steady = [100 + 6 * i for i in range(len(SNAPS))]
    series = _mk_series({"fragile": flat_then_jump,
                         **{f"s{i}": steady for i in range(5)}}, SNAPS)
    cohorts = {"fragile": "c", **{f"s{i}": "c" for i in range(5)}}
    _E, R, per = votes_at_cutoff(series, cohorts, SNAPS)
    assert per["fragile"]["unstable"] is True
    assert "fragile" not in R
    # steady growers are not vetoed
    assert all(not per[f"s{i}"]["unstable"] for i in range(5))


def test_canary_holds_on_disagreement():
    per_entity = {}
    # 5 entities: fitted slope positive but endpoint DOWN (poisoned-slope shape)
    for i in range(5):
        per_entity[f"bad{i}"] = {"cohort": "c", "slope": 0.1, "endpoint_up": False}
    stats = canary(per_entity)
    assert stats["c"]["agreement"] == 0.0
    assert stats["c"]["hold"] is True


def test_canary_passes_on_agreement():
    per_entity = {f"g{i}": {"cohort": "c", "slope": 0.1, "endpoint_up": True}
                  for i in range(5)}
    stats = canary(per_entity)
    assert stats["c"]["agreement"] == 1.0
    assert stats["c"]["hold"] is False
    assert CANARY_AGREEMENT_FLOOR == 0.8


def test_theil_sen_matches_ols_on_clean_linear():
    ys = [math.log1p(100 + 10 * i) for i in range(10)]
    assert (_ols_slope(ys) > 0) == (_theil_sen_slope(ys) > 0)



def test_two_member_cohort_rounding_residue_is_zero():
    # Two members of different size fit the residualizing line exactly: both z are 0. A one-ulp
    # residue (platform libm) must not become -1/1.4826 = -0.674 (2026-10-03, Kokoro-82M).
    from evaluate_axis3_v2h1 import _robust_z
    vals = {"a": (4.77912349311153, 0.03605302477819057), "b": (5.942799375126701, 0.00864513421882937)}
    for eid in vals:
        for direction in (math.inf, -math.inf):
            nudged = dict(vals)
            x, y = nudged[eid]
            nudged[eid] = (x, math.nextafter(y, direction))
            assert _robust_z(nudged, exact_pair=True) == {"a": 0.0, "b": 0.0}
    # the pinned m3/m4 arithmetic is unchanged while the flag is off
    lo = dict(vals, a=(vals["a"][0], math.nextafter(vals["a"][1], -math.inf)))
    assert round(_robust_z(lo)["a"], 3) == -0.674


def test_exact_pair_leaves_larger_and_same_size_cohorts_alone():
    from evaluate_axis3_v2h1 import _robust_z
    # nearly collinear three-member cohort (review 2026-10-05): real small residuals keep their z
    near = {"a": (4.0, 0.03), "b": (5.0, 0.040000000001), "c": (7.0, 0.06)}
    assert _robust_z(near, exact_pair=True) == _robust_z(near)
    assert round(_robust_z(near, exact_pair=True)["b"], 2) == 2.7
    spread = {"a": (4.0, 0.03), "b": (5.0, 0.01), "c": (6.0, 0.05), "d": (4.5, 0.02)}
    assert _robust_z(spread, exact_pair=True) == _robust_z(spread)
    # two members of the same size: no residualizing line, the slope difference is real
    same = {"a": (5.0, 0.03), "b": (5.0, 0.01)}
    assert _robust_z(same, exact_pair=True) == _robust_z(same)
