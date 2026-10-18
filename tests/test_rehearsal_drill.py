import json
from pathlib import Path

import pytest
import yaml

from scripts import rehearsal_drill as drill
from scripts import hf_upload_snapshot as hf


def _files(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "web/src/lib").mkdir(parents=True)
    (root / "web/src/data/methodology-control-baselines").mkdir(parents=True)
    (root / "etl").mkdir()
    (root / "data/snapshots/2026-10-17").mkdir(parents=True)
    (root / "web/src/lib/methodology-registry.json").write_text(json.dumps({
        "versions": [
            {"version": "m4", "status": "superseded"},
            {"version": "m5", "status": "current"},
        ],
    }))
    (root / "web/src/data/methodology-control-baselines/m4.json").write_text('{"controls":{"old":"aa"}}\n')
    (root / "web/src/data/methodology-control-baselines/m5.json").write_text('{"controls":{"e_ONE":"bb"}}\n')
    (root / "web/src/lib/kept.ts").write_text("export const kept = 1;\n")
    (root / "etl/owner_types.json").write_text(json.dumps({
        "repos": {"acme/widget": {"owner_type": "Organization", "repo_id": 11, "full_name": "acme/widget"}},
    }))
    (root / "data/snapshots/2026-10-17/snapshot.json").write_text(json.dumps({
        "snapshot_date": "2026-10-17",
        "entities": [
            {"entity_id": "e_ONE", "name": "Example", "slug": "example", "github_repo": "acme/widget", "homepage": "https://example.test"},
            {"entity_id": "e_TWO", "name": "Other", "slug": "other", "github_repo": "acme/widget"},
        ],
    }))
    return root


def test_none_leaves_the_tree_unchanged(tmp_path):
    root = _tree(tmp_path)
    before = _files(root)
    drill.apply_drill(root, "none")
    assert _files(root) == before


def test_site_test_adds_one_failing_check(tmp_path):
    root = _tree(tmp_path)
    before = _files(root)
    drill.apply_drill(root, "site_test")
    created = root / "web/src/lib/__drill__.test.ts"
    assert "expect(1).toBe(2)" in created.read_text()
    after = _files(root)
    assert set(after) - set(before) == {"web/src/lib/__drill__.test.ts"}
    assert after["web/src/lib/kept.ts"] == before["web/src/lib/kept.ts"]


def test_canary_missing_removes_only_the_current_baseline(tmp_path):
    root = _tree(tmp_path)
    drill.apply_drill(root, "canary_missing")
    assert not (root / "web/src/data/methodology-control-baselines/m5.json").exists()
    assert (root / "web/src/data/methodology-control-baselines/m4.json").is_file()
    assert (root / "web/src/lib/kept.ts").is_file()


def test_hf_handle_is_caught_and_a_clean_candidate_is_not(tmp_path, monkeypatch):
    root = _tree(tmp_path)
    card = root / "distribution/hf"
    card.mkdir(parents=True)
    (card / "README.md").write_text('configs:\n  - data_files:\n        path: "2026-10-10/entities.csv"\n')
    handles = root / "web/src/data"
    (handles / "person-free-handles.json").write_text("[]")
    monkeypatch.setattr(hf, "REPO", root)
    monkeypatch.setattr(hf, "SNAPSHOTS", root / "data/snapshots")
    monkeypatch.setattr(hf, "CARD", card / "README.md")
    assert hf.main(["--date", "2026-10-17", "--dry-run"]) == 0
    before_other = json.loads((root / "data/snapshots/2026-10-17/snapshot.json").read_text())["entities"][1]
    drill.apply_drill(root, "hf_handle", "2026-10-17")
    snap = json.loads((root / "data/snapshots/2026-10-17/snapshot.json").read_text())
    assert snap["entities"][0]["github_repo"] == "drill-person-handle/repo"
    assert snap["entities"][1] == before_other
    owners = json.loads((root / "etl/owner_types.json").read_text())["repos"]
    assert owners["acme/widget"]["owner_type"] == "Organization"
    user = owners["drill-person-handle/home"]
    assert user["owner_type"] == "User"
    assert user["full_name"].startswith("drill-person-handle/")
    assert hf.main(["--date", "2026-10-17", "--dry-run"]) == 3


def test_place_replay_reads_nested_and_flat_artifacts(tmp_path):
    nested = tmp_path / "nested/snapshot-2026-10-17-42/data/snapshots/2026-10-17"
    nested.mkdir(parents=True)
    (nested / "snapshot.json").write_text(json.dumps({"snapshot_date": "2026-10-17", "entities": []}))
    (nested / "manifest.json").write_text("{}\n")
    summary = tmp_path / "nested/snapshot-2026-10-17-42/evx-summary"
    summary.mkdir()
    (summary / "summary-graphql.json").write_text('{"repos": 1, "departed": []}\n')
    data = tmp_path / "data"
    out = tmp_path / "summary"
    data.mkdir()
    (data / "latest.json").write_text(json.dumps({"snapshot_date": "2026-10-10", "snapshot_id": "old"}))
    assert drill.place_replay(tmp_path / "nested", data, out) == "2026-10-17"
    assert json.loads((data / "latest.json").read_text())["snapshot_date"] == "2026-10-17"
    assert (data / "snapshots/2026-10-17/manifest.json").is_file()
    assert json.loads((out / "summary-graphql.json").read_text())["repos"] == 1

    flat = tmp_path / "flat/snapshot-2026-10-18-7"
    flat.mkdir(parents=True)
    (flat / "snapshot.json").write_text(json.dumps({"snapshot_date": "2026-10-18"}))
    (flat / "jobs.json").write_text("{}\n")
    (flat / "summary-graphql.json").write_text('{"repos": 2, "departed": []}\n')
    assert drill.place_replay(tmp_path / "flat", data, out) == "2026-10-18"
    placed = data / "snapshots/2026-10-18"
    assert (placed / "snapshot.json").is_file()
    assert not (placed / "jobs.json").exists()
    assert not (placed / "summary-graphql.json").exists()


def test_place_replay_rejects_a_date_mismatch(tmp_path):
    folder = tmp_path / "snapshot-2026-10-18-1"
    folder.mkdir()
    (folder / "snapshot.json").write_text(json.dumps({"snapshot_date": "2026-10-17"}))
    with pytest.raises(SystemExit, match="artifact name date"):
        drill.place_replay(tmp_path, tmp_path / "data", None)


def test_drill_verdict_phrases():
    passed = {"hf": "success", "verify": "success", "report": "success"}
    assert drill.drill_verdict("none", passed) == ("drill none: checks passed", 0)
    site = {"hf": "success", "verify": "failure", "report": "success"}
    assert drill.drill_verdict("site_test", site) == (
        "drill site_test: caught at step Verify the site against this rehearsal candidate", 0)
    assert drill.drill_verdict("hf_handle", passed) == ("drill hf_handle: NOT caught", 1)
    assert drill.drill_verdict("canary_missing", {"hf": "success", "verify": "failure", "report": "failure"}) == (
        "drill canary_missing: caught at step Verify the site against this rehearsal candidate", 0)
    # An unrelated failure is not a catch: the HF guard must catch the leaked handle itself.
    assert drill.drill_verdict("hf_handle", {"hf": "success", "verify": "success", "report": "failure"}) == (
        "drill hf_handle: NOT caught", 1)
    assert drill.drill_verdict("site_test", {"hf": "failure", "verify": "failure", "report": "success"})[1] == 1
    assert drill.drill_verdict("none", {"hf": "failure", "verify": "skipped", "report": "skipped"}) == (
        "drill none: failed at step Check the HF publication projection", 1)


def test_replay_workflow_does_not_alert_and_weekly_alerts_once():
    root = Path(__file__).resolve().parent.parent
    weekly = yaml.safe_load((root / ".github/workflows/weekly-snapshot.yml").read_text())
    steps = weekly["jobs"]["snapshot"]["steps"]
    alerts = [step for step in steps if "rehearsal-alert.mjs" in step.get("run", "")]
    assert alerts == [steps[-1]]
    assert alerts[0]["if"] == "${{ failure() && inputs.mode == 'rehearsal' }}"
    replay_path = root / ".github/workflows/rehearsal-replay.yml"
    replay_text = replay_path.read_text()
    replay = yaml.safe_load(replay_text)
    assert "rehearsal-alert" not in replay_text
    assert replay["concurrency"]["group"] == "rehearsal-replay"
    assert "data-commits" not in replay_text
    assert replay["permissions"] == {"contents": "read", "actions": "read"}
    inputs = replay[True]["workflow_dispatch"]["inputs"]
    assert inputs["source_run"]["required"] is True
    assert inputs["drill"]["default"] == "none"
    assert inputs["drill"]["options"] == ["none", "site_test", "hf_handle", "canary_missing"]
