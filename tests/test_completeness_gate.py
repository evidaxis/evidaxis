"""completeness_gate: records gaps (never silent), tolerates transient drops,
fails only on structural loss.

The 2026-07-01 bug was SILENCE, not the drop itself. So: always write dropped.json;
proceed on a small transient fraction (a handful of GitHub /stats 202s); fail only
when the loss is structural (> MAX_DROP_FRAC or zero captured).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import completeness_gate as cg


def _fixture(tmp_path, seeded_repos, present_ids, tracked_ids):
    (tmp_path / "etl").mkdir()
    id_map = {r: f"e_{i:011d}" for i, r in enumerate(seeded_repos)}
    (tmp_path / "etl" / "id_map.json").write_text(json.dumps(id_map))
    seeds = {"verticals": {"v": {"entities": [{"github_repo": r} for r in seeded_repos]}}}
    (tmp_path / "etl" / "seeds.json").write_text(json.dumps(seeds))
    snap_dir = tmp_path / "data" / "snapshots" / "2026-07-03"
    snap_dir.mkdir(parents=True)
    (snap_dir / "snapshot.json").write_text(json.dumps(
        {"entities": [{"entity_id": id_map[r]} for r in seeded_repos if id_map[r] in present_ids]}))
    hist = tmp_path / "data" / "history"
    hist.mkdir(parents=True)
    for eid in tracked_ids:
        (hist / f"{eid}.jsonl").write_text("{}\n")
    return tmp_path, id_map, snap_dir


def test_small_transient_drop_proceeds_and_is_recorded(tmp_path, monkeypatch):
    repos = [f"o/r{i}" for i in range(20)]
    tp, _idm, snap_dir = _fixture(tmp_path, repos, present_ids={eid for eid in
        [f"e_{i:011d}" for i in range(20)]} - {"e_00000000000"}, tracked_ids={"e_00000000000"})
    monkeypatch.setattr(cg, "REPO", tp)
    rc = cg.run("2026-07-03")
    assert rc == 0, "1/20 = 5% transient drop must proceed"
    report = json.loads((snap_dir / "dropped.json").read_text())
    assert report["in_snapshot"] == 19 and len(report["dropped"]) == 1
    assert report["dropped"][0]["previously_tracked"] is True  # gap is DECLARED, not silent


def test_structural_drop_fails(tmp_path, monkeypatch):
    repos = [f"o/r{i}" for i in range(20)]
    present = {f"e_{i:011d}" for i in range(10)}  # lost half
    tp, _idm, snap_dir = _fixture(tmp_path, repos, present_ids=present, tracked_ids=set())
    monkeypatch.setattr(cg, "REPO", tp)
    assert cg.run("2026-07-03") == 1, "50% loss is structural -> fail"
    assert (snap_dir / "dropped.json").exists()  # still recorded


def test_zero_captured_fails(tmp_path, monkeypatch):
    repos = [f"o/r{i}" for i in range(5)]
    tp, _idm, _snap_dir = _fixture(tmp_path, repos, present_ids=set(), tracked_ids=set())
    monkeypatch.setattr(cg, "REPO", tp)
    assert cg.run("2026-07-03") == 1


def test_clean_snapshot_passes(tmp_path, monkeypatch):
    repos = [f"o/r{i}" for i in range(10)]
    present = {f"e_{i:011d}" for i in range(10)}
    tp, _idm, snap_dir = _fixture(tmp_path, repos, present_ids=present, tracked_ids=set())
    monkeypatch.setattr(cg, "REPO", tp)
    assert cg.run("2026-07-03") == 0
    assert json.loads((snap_dir / "dropped.json").read_text())["dropped"] == []
