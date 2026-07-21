"""Mutation tests for the data-sanity gate (council: Pro voice #6 — inject
synthetic corruption classes; the detector must catch the catchable and stay
silent on clean data). Pure-function tests over the reversal metric and
calibration primitives — no BigQuery, no filesystem writes."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collectors"))

from data_sanity_gate import (
    COVERAGE_MIN,
    RECOVERY_WINDOW,
    VALUE_FLOOR,
    max_clean_move,
    reversal_share,
)


def _series(rows):
    """rows: {entity: [v0, v1, ...]} -> series dict keyed by synthetic dates."""
    snaps = [f"2026-01-{d:02d}" for d in range(1, max(len(v) for v in rows.values()) + 1)]
    return ({e: {snaps[i]: v for i, v in enumerate(vals)} for e, vals in rows.items()},
            snaps)


BOUND = math.log(2)  # the physical-floor move bound derived in calibration


def test_clean_growth_is_silent():
    series, snaps = _series({f"e{i}": [100 + i, 110 + i, 121 + i, 133 + i]
                             for i in range(12)})
    for i in range(1, len(snaps) - 1):
        share, eligible = reversal_share(series, snaps, i, BOUND)
        assert eligible >= 10
        assert share == 0.0


def test_panel_wide_dip_and_recover_fires():
    # the incident shape: collapse ~99% then full recovery
    series, snaps = _series({f"e{i}": [1000, 10, 1050, 1080] for i in range(12)})
    share, eligible = reversal_share(series, snaps, 1, BOUND)
    assert eligible >= 10
    assert share == 1.0


def test_spike_and_revert_fires_symmetrically():
    # upward corruption must be caught the same way (anti positive-laundering)
    series, snaps = _series({f"e{i}": [100, 5000, 102, 104] for i in range(12)})
    share, _ = reversal_share(series, snaps, 1, BOUND)
    assert share == 1.0


def test_consecutive_corrupt_pair_first_partition_fires():
    # two corrupt partitions in a row: recovery is only visible 2 steps out —
    # RECOVERY_WINDOW=2 must still catch the first one
    assert RECOVERY_WINDOW >= 2
    series, snaps = _series({f"e{i}": [1000, 12, 9, 1020] for i in range(12)})
    share, _ = reversal_share(series, snaps, 1, BOUND)
    assert share == 1.0


def test_sustained_level_shift_does_not_fire_reversal():
    # a real regime change (drop WITHOUT recovery) is NOT a reversal — the
    # rule must not censor genuine declines (honesty: this class is handled
    # by other layers, not silently deleted)
    series, snaps = _series({f"e{i}": [1000, 400, 390, 395] for i in range(12)})
    share, _ = reversal_share(series, snaps, 1, BOUND)
    assert share == 0.0


def test_single_entity_anomaly_stays_below_panel_threshold():
    rows = {f"e{i}": [100, 104, 108, 112] for i in range(11)}
    rows["weird"] = [100, 2, 100, 104]  # one entity dips and recovers
    series, snaps = _series(rows)
    share, eligible = reversal_share(series, snaps, 1, BOUND)
    assert eligible == 12
    assert share <= 1 / 12 + 1e-9  # a lone entity cannot look panel-wide


def test_value_floor_excludes_noise_entities():
    # tiny-value entities (< VALUE_FLOOR) are ineligible for the shock metric
    series, snaps = _series({f"e{i}": [VALUE_FLOOR - 1, 0, VALUE_FLOOR - 1, VALUE_FLOOR - 1]
                             for i in range(12)})
    share, eligible = reversal_share(series, snaps, 1, BOUND)
    assert eligible == 0
    assert share == 0.0


def test_calibration_excludes_challenge_partitions():
    series, snaps = _series({f"e{i}": [100, 3, 105, 108] for i in range(12)})
    corrupt_snap = snaps[1]
    _max_move, max_share, transitions = max_clean_move(
        {"s": series}, exclude_snaps={corrupt_snap})
    # with the corrupt transition excluded, clean history shows no big moves
    assert max_share == 0.0
    assert all(t["to"] != corrupt_snap for t in transitions)


def test_coverage_floor_is_the_preregistered_constant():
    # the stage-1 contract must use the pre-registered promotion floor (30),
    # not a new post-incident number
    assert COVERAGE_MIN == 30
