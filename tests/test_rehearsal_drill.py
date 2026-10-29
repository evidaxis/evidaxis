import json
import shutil
import subprocess
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


def test_place_replay_reads_nested_and_flat_artifacts(tmp_path, capsys):
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
    assert capsys.readouterr().out.splitlines().count(drill.SNAPSHOT_ONLY_NOTICE) == 2


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
    # The site guard also rejects the leaked handle; that second catch keeps the drill green.
    assert drill.drill_verdict("hf_handle", {"hf": "failure", "verify": "failure", "report": "failure"}) == (
        "drill hf_handle: caught at step Check the HF publication projection", 0)
    assert drill.drill_verdict("none", {"hf": "failure", "verify": "skipped", "report": "skipped"}) == (
        "drill none: failed at step Check the HF publication projection", 1)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _capture_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    for relative in ("data/kept.txt", "data/gone.txt", "etl/owner_types.json", "relationships.tsv", "web/kept.ts"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
    (root / "data/kept.txt").write_text("base-data\n")
    (root / "data/gone.txt").write_text("gone\n")
    (root / "data/latest.json").write_text('{"snapshot_date": "2026-10-17"}\n')
    (root / "etl/owner_types.json").write_text('{"repos": {"acme/widget": "Organization"}}\n')
    (root / "relationships.tsv").write_text("base\n")
    (root / "web/kept.ts").write_text("export const kept = 1;\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "base")
    base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    (root / "etl/owner_types.json").write_text('{"repos": {"acme/widget": "User"}}\n')
    (root / "data/gone.txt").unlink()
    (root / "data/history").mkdir()
    (root / "data/history/e_1.jsonl").write_text('{"n": 1}\n')
    snap = root / "data/snapshots/2026-10-24"
    snap.mkdir(parents=True)
    (snap / "snapshot.json").write_text(json.dumps({"snapshot_date": "2026-10-24", "entities": []}))
    (root / "data/latest.json").write_text('{"snapshot_date": "2026-10-24"}\n')
    (root / "relationships.tsv").write_text("capture\n")
    (root / "web/kept.ts").write_text("export const kept = 'capture';\n")
    return root, base


def test_pack_and_place_rebuild_capture_data_and_keep_code_under_test(tmp_path, capsys):
    root, base = _capture_repo(tmp_path)
    packed = tmp_path / "evx-candidate"
    manifest = drill.pack_candidate(root, packed)
    by_path = {item["path"]: item["status"] for item in manifest["paths"]}
    assert manifest["base_sha"] == base
    assert by_path["data/gone.txt"] == "D"
    assert by_path["etl/owner_types.json"] == "M"
    assert by_path["data/history/e_1.jsonl"] == "A"
    assert by_path["relationships.tsv"] == "M"
    assert by_path["web/kept.ts"] == "M"
    assert "data/kept.txt" not in by_path
    upload_snap = tmp_path / "snap-copy"
    shutil.copytree(root / "data/snapshots/2026-10-24", upload_snap)
    _git(root, "checkout", "--", ".")
    _git(root, "clean", "-fd")
    (root / "web/kept.ts").write_text("export const kept = 'under-test';\n")
    (root / "data/later.txt").write_text("later\n")
    (root / "data/kept.txt").write_text("main-data\n")
    (root / "etl/owner_types.json").write_text('{"repos": {"acme/widget": "main"}}\n')
    (root / "relationships.tsv").write_text("main\n")
    (root / "data/latest.json").write_text('{"snapshot_date": "2026-10-31"}\n')
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "under test")
    download = tmp_path / "dl/snapshot-2026-10-24-9"
    shutil.copytree(upload_snap, download / "data/snapshots/2026-10-24")
    shutil.copytree(packed, download / "evx-candidate")
    summary = download / "evx-summary"
    summary.mkdir()
    (summary / "summary-graphql.json").write_text('{"repos": 3, "departed": []}\n')
    assert drill.place_replay(download, root / "data", tmp_path / "summary", root) == "2026-10-24"
    assert json.loads((root / "etl/owner_types.json").read_text())["repos"]["acme/widget"] == "User"
    assert not (root / "data/gone.txt").exists()
    assert not (root / "data/later.txt").exists()
    assert (root / "data/kept.txt").read_text() == "base-data\n"
    assert (root / "data/history/e_1.jsonl").read_text() == '{"n": 1}\n'
    assert json.loads((root / "data/snapshots/2026-10-24/snapshot.json").read_text())["snapshot_date"] == "2026-10-24"
    assert json.loads((root / "data/latest.json").read_text())["snapshot_date"] == "2026-10-24"
    assert (root / "relationships.tsv").read_text() == "main\n"
    assert (root / "web/kept.ts").read_text() == "export const kept = 'under-test';\n"
    assert json.loads((tmp_path / "summary/summary-graphql.json").read_text())["repos"] == 3
    assert drill.SNAPSHOT_ONLY_NOTICE not in capsys.readouterr().out


def _script_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "scripts").mkdir()
    (root / "data").mkdir()
    (root / "etl").mkdir()
    (root / "scripts/ci-alert.mjs").write_text("original\n")
    (root / "data/ok.txt").write_text("data\n")
    (root / "etl/ok.json").write_text("{}\n")
    (root / "data/hooked").symlink_to("../scripts/ci-alert.mjs")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "base")
    base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    return root, base


def _attack_manifest(tmp_path: Path, base: str, paths: list[dict], blobs: dict[str, str] | None = None) -> Path:
    out = tmp_path / "candidate"
    if out.exists():
        shutil.rmtree(out)
    files = out / "files"
    files.mkdir(parents=True)
    for rel, body in (blobs or {}).items():
        dest = files / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body)
    manifest = out / "candidate-manifest.json"
    manifest.write_text(json.dumps({"base_sha": base, "paths": paths}) + "\n")
    return manifest


def test_apply_candidate_rejects_paths_that_can_overwrite_code(tmp_path):
    root, base = _script_repo(tmp_path)
    script = root / "scripts/ci-alert.mjs"
    outside = tmp_path / "abs-target.mjs"
    attacks = [
        ([{"path": "./scripts/ci-alert.mjs", "status": "M"}], {"scripts/ci-alert.mjs": "pwned\n"}),
        ([{"path": "data/../scripts/x", "status": "M"}], {"scripts/x": "pwned\n"}),
        ([{"path": str(outside), "status": "M"}], {}),
        ([{"path": "data/hooked", "status": "M"}], {"data/hooked": "pwned\n"}),
    ]
    for paths, blobs in attacks:
        before = script.read_text()
        manifest = _attack_manifest(tmp_path, base, paths, blobs)
        with pytest.raises(SystemExit):
            drill.apply_candidate(root, manifest)
        assert script.read_text() == before
        assert not (root / "scripts/x").exists()
        assert not outside.exists()
        assert (root / "data/hooked").is_symlink()


def test_apply_candidate_rejects_duplicate_paths_before_writing(tmp_path):
    root, base = _script_repo(tmp_path)
    manifest = _attack_manifest(tmp_path, base, [
        {"path": "data/fresh.txt", "status": "A"},
        {"path": "data/fresh.txt", "status": "A"},
    ], {"data/fresh.txt": "x\n"})
    with pytest.raises(SystemExit):
        drill.apply_candidate(root, manifest)
    assert not (root / "data/fresh.txt").exists()


def test_select_source_uses_the_newest_live_rehearsal():
    runs = [
        {"databaseId": 4, "displayTitle": "weekly rehearsal 2026-10-31", "status": "in_progress"},
        {"databaseId": 3, "displayTitle": "weekly release 2026-10-24", "status": "completed"},
        {"databaseId": 2, "displayTitle": "weekly rehearsal 2026-10-24", "status": "completed"},
        {"databaseId": 1, "displayTitle": "weekly rehearsal 2026-10-17", "status": "completed"},
    ]
    assert drill.select_source(runs, lambda run_id: run_id == 1) == 1
    assert drill.select_source(runs, lambda run_id: run_id in {1, 2}) == 2
    assert drill.select_source(runs, lambda run_id: False) is None


def test_select_keeps_an_explicit_run_and_notices_when_none_are_live(tmp_path, monkeypatch, capsys):
    out = tmp_path / "gh-out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("SOURCE_RUN", "4242")
    assert drill.main(["select"]) == 0
    assert out.read_text() == "found=true\nrun_id=4242\n"
    out.write_text("")
    monkeypatch.setenv("SOURCE_RUN", " ")
    monkeypatch.setattr(drill, "_weekly_runs", lambda: [
        {"databaseId": 9, "displayTitle": "weekly release 2026-10-24", "status": "completed"},
    ])
    monkeypatch.setattr(drill, "_snapshot_artifact_live", lambda run_id: True)
    assert drill.main(["select"]) == 0
    assert out.read_text() == "found=false\n"
    assert drill.NO_CANDIDATE_NOTICE in capsys.readouterr().out


def test_replay_workflow_does_not_alert_and_weekly_alerts_once():
    root = Path(__file__).resolve().parent.parent
    weekly = yaml.safe_load((root / ".github/workflows/weekly-snapshot.yml").read_text())
    steps = weekly["jobs"]["snapshot"]["steps"]
    alerts = [step for step in steps if "rehearsal-alert.mjs" in step.get("run", "")]
    assert alerts == [steps[-1]]
    assert alerts[0]["if"] == "${{ failure() && inputs.mode == 'rehearsal' }}"
    packed = [step for step in steps if "rehearsal_drill.py pack" in step.get("run", "")]
    assert len(packed) == 1
    upload = next(step for step in steps if str(step.get("name", "")).startswith("Upload snapshot"))
    assert steps.index(packed[0]) < steps.index(upload)
    assert "evx-candidate" in upload["with"]["path"]
    assert 'MODE" = "rehearsal"' in packed[0]["run"] or '"$MODE" = "rehearsal"' in packed[0]["run"]
    replay_path = root / ".github/workflows/rehearsal-replay.yml"
    replay_text = replay_path.read_text()
    replay = yaml.safe_load(replay_text)
    assert "rehearsal-alert" not in replay_text
    assert replay["concurrency"]["group"] == "rehearsal-replay"
    assert "data-commits" not in replay_text
    assert replay["permissions"] == {"contents": "read", "actions": "read"}
    triggers = replay[True]
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["source_run"]["required"] is True
    assert inputs["drill"]["default"] == "none"
    assert inputs["drill"]["options"] == ["none", "site_test", "hf_handle", "canary_missing"]
    push = triggers["push"]
    assert push["branches"] == ["main"]
    assert "web/**" in push["paths"]
    assert "web/package.json" in push["paths"]
    assert "web/package-lock.json" in push["paths"]
    replay_steps = replay["jobs"]["replay"]["steps"]
    assert replay_steps[0]["with"]["fetch-depth"] == 0
    # A queued push must replay the commit that triggered it, not whatever main is now.
    assert replay_steps[0]["with"]["ref"] == "${{ github.event_name == 'push' && github.sha || 'main' }}"
    select = next(step for step in replay_steps if step.get("id") == "source")
    assert "rehearsal_drill.py select" in select["run"]
    keeper = [step for step in replay_steps if "ci-alert.mjs" in step.get("run", "")]
    assert len(keeper) == 1
    assert keeper[0]["if"] == "${{ failure() && github.event_name == 'push' }}"
    assert keeper[0]["env"]["TELEGRAM_BOT_TOKEN"] == "${{ secrets.TELEGRAM_BOT_TOKEN }}"
    assert keeper[0]["env"]["ALERT_CHAT_ID"] == "${{ secrets.ALERT_TG_CHAT_ID }}"


def test_ci_on_main_alerts_the_keeper_from_the_existing_secrets():
    root = Path(__file__).resolve().parent.parent
    for name, needed in (("web-ci", "build-test-verify"), ("python-ci", "test")):
        body = yaml.safe_load((root / ".github/workflows" / f"{name}.yml").read_text())
        alert = body["jobs"]["alert"]
        assert alert["needs"] == needed
        assert "always()" in alert["if"]
        assert f"needs.{needed}.result == 'failure'" in alert["if"]
        assert "refs/heads/main" in alert["if"]
        assert "workflow_run.head_branch == 'main'" in alert["if"]
        assert alert["permissions"] == {"contents": "read", "actions": "read"}
        step = alert["steps"][-1]
        assert step["run"] == "node scripts/ci-alert.mjs"
        assert step["env"]["TELEGRAM_BOT_TOKEN"] == "${{ secrets.TELEGRAM_BOT_TOKEN }}"
        assert step["env"]["ALERT_CHAT_ID"] == "${{ secrets.ALERT_TG_CHAT_ID }}"
        assert "secrets." not in step["run"]
        uses = [item.get("uses", "") for item in alert["steps"]]
        assert "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5" in uses
        assert "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020" in uses
