"""The event writers must be reachable on failures and unreachable in rehearsal."""
from pathlib import Path

import yaml


def workflow(name):
    return yaml.safe_load(Path(f".github/workflows/{name}.yml").read_text())


def test_status_permissions_only_on_writer_jobs():
    writers = {("weekly-snapshot", "snapshot"), ("deploy-web", "deploy"), ("hf-mirror", "mirror")}
    found = set()
    for path in Path(".github/workflows").glob("*.yml"):
        body = yaml.safe_load(path.read_text())
        assert body.get("permissions", {}).get("statuses") != "write"
        for name, job in body["jobs"].items():
            if job.get("permissions", {}).get("statuses") == "write":
                found.add((path.stem, name))
    assert found == writers
    for name in ("liveness-check", "workflow-watchdog"):
        assert workflow(name)["permissions"]["statuses"] == "read"


def test_weekly_receipts_follow_commit_and_readback_and_cannot_run_in_rehearsal():
    steps = workflow("weekly-snapshot")["jobs"]["snapshot"]["steps"]
    indexed = {step["id"]: (n, step) for n, step in enumerate(steps) if "id" in step}
    assert indexed["commit"][0] < indexed["captured"][0] < indexed["hf"][0]
    assert 'capture "$SNAPSHOT_DATE"' in indexed["captured"][1]["run"]
    assert 'hf_upload_snapshot.py --date "$SNAPSHOT_DATE"' in indexed["hf"][1]["run"]
    writers = [step for step in steps if "release-status.mjs" in step.get("run", "")]
    assert len(writers) == 2
    for step in writers:
        assert "inputs.mode != 'rehearsal'" in step["if"]
    final = writers[-1]
    assert steps.index(final) > indexed["hf"][0]
    assert "always()" in final["if"]
    assert "steps.captured.outcome == 'success'" in final["if"]
    assert final["env"]["RELEASE_SHA"] == "${{ steps.captured.outputs.sha }}"
    assert final["env"]["RELEASE_STEPS"] == "${{ toJSON(steps) }}"


def test_deploy_records_receipt_on_resolved_commit_even_on_failure():
    body = workflow("deploy-web")
    steps = body["jobs"]["deploy"]["steps"]
    indexed = {step["id"]: (n, step) for n, step in enumerate(steps) if "id" in step}
    assert indexed["release"][0] < indexed["secrets"][0] < indexed["build"][0] < indexed["deploy"][0] < indexed["receipt"][0]
    assert 'prepare "$DATE"' in indexed["release"][1]["run"]
    assert '${PRODUCER_TITLE#weekly release }' in indexed["release"][1]["run"]
    assert "release_date" in body[True]["workflow_dispatch"]["inputs"]
    assert indexed["receipt"][1]["env"]["RELEASE_DATE"] == "${{ steps.release.outputs.date }}"
    final = steps[-1]
    assert final["run"] == "node scripts/release-status.mjs record deployed"
    assert "always()" in final["if"]
    assert "steps.release.outcome == 'success'" in final["if"]
    assert final["env"]["RELEASE_SHA"] == "${{ steps.release.outputs.sha }}"
    assert final["env"]["RELEASE_STEPS"] == "${{ toJSON(steps) }}"


def test_manual_hf_repair_uses_the_same_receipt_writer():
    steps = workflow("hf-mirror")["jobs"]["mirror"]["steps"]
    assert 'node scripts/release-status.mjs hf "$date"' in steps[-1]["run"]
    assert steps[-1]["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert any('"huggingface_hub==2.2.0"' in step.get("run", "") for step in steps)
