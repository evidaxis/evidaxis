"""Tests for collectors/counts_check.py — status vocabulary integrity (C3)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
import counts_check as cc


def _entity(status: str, axis2: str = "absent") -> dict:
    return {
        "entity_id": f"e_{status}_{axis2}",
        "status": status,
        "axes": {
            "openalex_citation_momentum": {"status": axis2},
        },
    }


def test_expected_counts_is_pure_counter():
    ents = [
        _entity("rising", "present"),
        _entity("watch", "present"),
        _entity("tracked", "present"),
        _entity("single-axis", "absent"),
        _entity("single-axis", "absent"),
        _entity("calibration", "insufficient"),
    ]
    exp = cc.expected_counts(ents)
    assert exp["entities"] == 6
    assert exp["rising"] == 1
    assert exp["watch"] == 1
    assert exp["tracked"] == 1
    assert exp["single-axis"] == 2
    assert exp["calibration"] == 1
    assert exp["axis2_present"] == 3  # rising, watch, tracked present


def test_legacy_fold_merges_single_axis_into_tracked():
    ents = [
        _entity("tracked"),
        _entity("single-axis"),
        _entity("single-axis"),
        _entity("watch"),
    ]
    leg = cc.legacy_fold_counts(ents)
    assert leg["tracked"] == 3  # 1 tracked + 2 single-axis
    assert "single-axis" not in leg
    assert leg["watch"] == 1


def test_check_passes_legacy_shape():
    ents = [
        _entity("watch", "present"),
        _entity("tracked", "present"),
        _entity("single-axis"),
        _entity("calibration"),
    ]
    snap = {
        "counts": {
            "entities": 4,
            "rising": 0,
            "watch": 1,
            "tracked": 2,  # tracked + single-axis
            "calibration": 1,
            "axis2_present": 2,
        },
        "entities": ents,
    }
    assert cc.check_snapshot(snap) == []


def test_check_fails_when_legacy_tracked_wrong():
    ents = [_entity("tracked"), _entity("single-axis")]
    snap = {
        "counts": {
            "entities": 2,
            "rising": 0,
            "watch": 0,
            "tracked": 1,  # should be 2 under fold
            "calibration": 0,
            "axis2_present": 0,
        },
        "entities": ents,
    }
    fails = cc.check_snapshot(snap)
    assert any("tracked" in f for f in fails)


def test_check_pure_when_single_axis_key_present():
    ents = [
        _entity("tracked", "present"),
        _entity("single-axis"),
        _entity("watch", "present"),
    ]
    # Honest shape: single-axis key present → pure Counter required.
    good = {
        "counts": {
            "entities": 3,
            "rising": 0,
            "watch": 1,
            "tracked": 1,
            "single-axis": 1,
            "calibration": 0,
            "axis2_present": 2,
        },
        "entities": ents,
    }
    assert cc.check_snapshot(good) == []

    # Legacy fold numbers with a single-axis key must fail.
    bad = {
        "counts": {
            "entities": 3,
            "rising": 0,
            "watch": 1,
            "tracked": 2,  # folded
            "single-axis": 1,  # key present → pure required
            "calibration": 0,
            "axis2_present": 2,
        },
        "entities": ents,
    }
    fails = cc.check_snapshot(bad)
    assert any("tracked" in f for f in fails)


def test_strict_rejects_legacy_fold():
    ents = [_entity("tracked"), _entity("single-axis")]
    snap = {
        "counts": {
            "entities": 2,
            "rising": 0,
            "watch": 0,
            "tracked": 2,
            "calibration": 0,
            "axis2_present": 0,
        },
        "entities": ents,
    }
    assert cc.check_snapshot(snap) == []  # legacy ok
    fails = cc.check_snapshot(snap, strict=True)
    assert any("tracked" in f or "single-axis" in f for f in fails)


def test_check_passes_on_live_latest():
    """Acceptance: python collectors/counts_check.py --check on live archive."""
    date = cc.load_latest_date()
    assert cc.check_date(date) == 0
