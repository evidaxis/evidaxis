"""Tests for collectors/snapshot_identity.py — content-addressed snapshot_id post-step."""
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
import snapshot_identity as si


def _minimal_snap(entities, snapshot_id="deadbeef0000", date="2026-07-10", period="2026-w28"):
    return {
        "schema_version": "1.0",
        "snapshot_date": date,
        "period": period,
        "methodology_version": "m2",
        "snapshot_id": snapshot_id,
        "entities": entities,
        "counts": {"entities": len(entities)},
    }


def test_content_id_changes_when_payload_differs():
    a = _minimal_snap([{"entity_id": "e_A", "momentum": 1.0}])
    b = _minimal_snap([{"entity_id": "e_A", "momentum": 2.0}])  # different score
    assert si.content_snapshot_id(a) != si.content_snapshot_id(b)
    # same payload → same id regardless of stored snapshot_id field
    c = dict(a)
    c["snapshot_id"] = "ffffffffffff"
    assert si.content_snapshot_id(a) == si.content_snapshot_id(c)


def test_rewrite_is_idempotent(tmp_path, monkeypatch):
    snap_dir = tmp_path / "data" / "snapshots" / "2026-07-10"
    snap_dir.mkdir(parents=True)
    path = snap_dir / "snapshot.json"
    snap = _minimal_snap([{"entity_id": "e_A", "momentum": 10.0}])
    path.write_text(json.dumps(snap, indent=2) + "\n")

    monkeypatch.setattr(si, "SNAPSHOTS", tmp_path / "data" / "snapshots")

    old1, new1, changed1 = si.rewrite_snapshot(path)
    assert changed1
    assert new1 != old1
    assert new1 == si.content_snapshot_id(json.loads(path.read_text()))
    assert len(new1) == 12

    old2, new2, changed2 = si.rewrite_snapshot(path)
    assert not changed2
    assert old2 == new2 == new1


def test_check_fails_on_synthetic_collision(tmp_path, monkeypatch):
    root = tmp_path / "data" / "snapshots"
    # Two dirs, same snapshot_id, different payloads.
    for date, mom in [("2026-08-01", 1.0), ("2026-08-02", 9.0)]:
        d = root / date
        d.mkdir(parents=True)
        snap = _minimal_snap(
            [{"entity_id": "e_X", "momentum": mom}],
            snapshot_id="aaaaaaaaaaaa",
            date=date,
        )
        (d / "snapshot.json").write_text(json.dumps(snap, indent=2) + "\n")

    monkeypatch.setattr(si, "SNAPSHOTS", root)
    monkeypatch.setattr(si, "ERRATA", tmp_path / "missing_errata.json")  # no allowlist
    assert si.check_collisions() == 1


def test_check_passes_allowlisted_pair(tmp_path, monkeypatch):
    root = tmp_path / "data" / "snapshots"
    hashes = {}
    for date, mom in [("2026-08-01", 1.0), ("2026-08-02", 9.0)]:
        d = root / date
        d.mkdir(parents=True)
        snap = _minimal_snap(
            [{"entity_id": "e_X", "momentum": mom}],
            snapshot_id="bbbbbbbbbbbb",
            date=date,
        )
        (d / "snapshot.json").write_text(json.dumps(snap, indent=2) + "\n")
        hashes[date] = si.payload_hash(snap)

    errata = tmp_path / "errata_snapshot_id.json"
    errata.write_text(
        json.dumps(
            {
                "version": 1,
                "allowlist": [
                    {
                        "snapshot_id": "bbbbbbbbbbbb",
                        "dates": ["2026-08-01", "2026-08-02"],
                        "payload_hashes": hashes,
                    }
                ],
            }
        )
    )

    monkeypatch.setattr(si, "SNAPSHOTS", root)
    monkeypatch.setattr(si, "ERRATA", errata)
    assert si.check_collisions() == 0


def test_check_passes_on_live_archive():
    """Current published data has the known f1f2495d518d pair, allowlisted."""
    # Use real paths (default module constants).
    assert si.SNAPSHOTS.is_dir()
    assert si.ERRATA.is_file()
    assert si.check_collisions() == 0


def test_recompute_on_copy_differs_from_stored_collision(tmp_path):
    """Acceptance: copy of 2026-07-04 gets a new id ≠ f1f2495d518d and ≠ 2026-07-03's recompute."""
    src_root = REPO / "data" / "snapshots"
    if not (src_root / "2026-07-04" / "snapshot.json").is_file():
        pytest.skip("published snapshots not present")
    for date in ("2026-07-03", "2026-07-04"):
        dest = tmp_path / date
        dest.mkdir()
        shutil.copy2(src_root / date / "snapshot.json", dest / "snapshot.json")
        old, new, changed = si.rewrite_snapshot(dest / "snapshot.json")
        assert old == "f1f2495d518d"
        assert changed
        assert new != "f1f2495d518d"
        assert len(new) == 12

    id03 = json.loads((tmp_path / "2026-07-03" / "snapshot.json").read_text())["snapshot_id"]
    id04 = json.loads((tmp_path / "2026-07-04" / "snapshot.json").read_text())["snapshot_id"]
    assert id03 != id04
    assert id03 == "38287b561ff9"
    assert id04 == "900232c1b32c"


def test_rewrite_updates_bundle_mirrors(tmp_path, monkeypatch):
    """manifest.json + provenance.json reference the id — must move in lockstep."""
    snap_dir = tmp_path / "data" / "snapshots" / "2026-07-11"
    snap_dir.mkdir(parents=True)
    path = snap_dir / "snapshot.json"
    snap = _minimal_snap([{"entity_id": "e_A", "momentum": 5.0}], date="2026-07-11")
    path.write_text(json.dumps(snap, indent=2) + "\n")
    for name in ("manifest.json", "provenance.json"):
        (snap_dir / name).write_text(
            json.dumps({"snapshot_id": "deadbeef0000", "other": 1}, indent=2) + "\n"
        )

    monkeypatch.setattr(si, "SNAPSHOTS", tmp_path / "data" / "snapshots")
    _old, new, changed = si.rewrite_snapshot(path)
    assert changed
    for name in ("manifest.json", "provenance.json"):
        doc = json.loads((snap_dir / name).read_text())
        assert doc["snapshot_id"] == new, name
        assert doc["other"] == 1  # untouched fields preserved


def test_check_fails_on_bundle_divergence(tmp_path, monkeypatch):
    """snapshot.json and manifest.json disagree on the id → --check fails."""
    d = tmp_path / "data" / "snapshots" / "2026-08-03"
    d.mkdir(parents=True)
    snap = _minimal_snap([{"entity_id": "e_Y", "momentum": 2.0}],
                         snapshot_id="cccccccccccc", date="2026-08-03")
    (d / "snapshot.json").write_text(json.dumps(snap, indent=2) + "\n")
    (d / "manifest.json").write_text(json.dumps({"snapshot_id": "dddddddddddd"}) + "\n")

    monkeypatch.setattr(si, "SNAPSHOTS", tmp_path / "data" / "snapshots")
    monkeypatch.setattr(si, "ERRATA", tmp_path / "missing_errata.json")
    assert si.check_collisions() == 1


def test_check_rejects_swapped_allowlist_hashes(tmp_path, monkeypatch):
    """An erratum with per-date hashes swapped is a WRONG erratum — no pass."""
    root = tmp_path / "data" / "snapshots"
    hashes = {}
    for date, mom in [("2026-08-01", 1.0), ("2026-08-02", 9.0)]:
        d = root / date
        d.mkdir(parents=True)
        snap = _minimal_snap([{"entity_id": "e_X", "momentum": mom}],
                             snapshot_id="eeeeeeeeeeee", date=date)
        (d / "snapshot.json").write_text(json.dumps(snap, indent=2) + "\n")
        hashes[date] = si.payload_hash(snap)

    swapped = {"2026-08-01": hashes["2026-08-02"], "2026-08-02": hashes["2026-08-01"]}
    errata = tmp_path / "errata_snapshot_id.json"
    errata.write_text(json.dumps({"version": 1, "allowlist": [
        {"snapshot_id": "eeeeeeeeeeee", "dates": list(swapped), "payload_hashes": swapped}
    ]}))

    monkeypatch.setattr(si, "SNAPSHOTS", root)
    monkeypatch.setattr(si, "ERRATA", errata)
    assert si.check_collisions() == 1
