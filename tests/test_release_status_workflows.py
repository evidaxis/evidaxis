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
    assert len(writers) == 3
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


def test_deploy_exposes_actual_checkout_before_resolving_or_publishing():
    steps = workflow("deploy-web")["jobs"]["deploy"]["steps"]
    record = next(step for step in steps if step.get("id") == "checkout")
    artifact = next(step for step in steps if step.get("name") == "Expose the actual checkout to release sensors")
    resolve = next(step for step in steps if step.get("id") == "release")
    assert steps.index(record) < steps.index(artifact) < steps.index(resolve)
    assert "SHA=$(git rev-parse HEAD)" in record["run"]
    assert 'echo "sha=$SHA" >> "$GITHUB_OUTPUT"' in record["run"]
    assert 'echo "$SHA" > "$RUNNER_TEMP/release-checkout.txt"' in record["run"]
    assert artifact["uses"] == "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
    assert artifact["with"]["name"] == "deploy-checkout-${{ github.run_attempt }}-${{ steps.checkout.outputs.sha }}"
    assert artifact["with"]["path"] == "${{ runner.temp }}/release-checkout.txt"
    assert artifact["with"]["if-no-files-found"] == "error"


def test_site_dispatch_precedes_hf_and_hf_failure_stays_red():
    body = workflow("weekly-snapshot")
    job = body["jobs"]["snapshot"]
    assert job["permissions"]["actions"] == "write"
    steps = job["steps"]
    indexed = {step["id"]: step for step in steps if "id" in step}
    dispatch = indexed["dispatch"]
    assert steps.index(indexed["captured"]) + 1 == steps.index(dispatch)
    assert steps.index(dispatch) < steps.index(indexed["hf"])
    assert dispatch["if"] == "${{ inputs.mode != 'rehearsal' && steps.captured.outcome == 'success' }}"
    assert dispatch["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert dispatch["run"] == 'node scripts/release-status.mjs dispatch "$SNAPSHOT_DATE"'
    # HF still runs if dispatch fails, and its error remains a job failure.
    assert indexed["hf"]["if"] == "${{ always() && inputs.mode != 'rehearsal' && steps.captured.outcome == 'success' }}"
    assert not job.get("continue-on-error")
    assert all(not step.get("continue-on-error") for step in steps)


def test_fallback_admits_failed_producer_and_serializes_duplicate_receipt_checks():
    body = workflow("deploy-web")
    assert body[True]["workflow_run"] == {"workflows": ["weekly-snapshot"], "types": ["completed"]}
    assert body["concurrency"] == {"group": "deploy-prod", "cancel-in-progress": False, "queue": "max"}
    job = body["jobs"]["deploy"]
    assert job["if"] == (
        "github.event_name != 'workflow_run' || "
        "(github.event.workflow_run.head_branch == 'main' &&\n "
        "startsWith(github.event.workflow_run.display_title, 'weekly release ') &&\n "
        "!endsWith(github.event.workflow_run.display_title, 'resolve-date'))"
    )
    steps = job["steps"]
    indexed = {step["id"]: step for step in steps if "id" in step}
    assert indexed["release"]["env"]["INPUT_DATE"] == "${{ inputs.release_date }}"
    for step_id in ["secrets", "node", "build", "deploy", "receipt"]:
        assert indexed[step_id]["if"] == "${{ steps.release.outputs.skip != 'true' }}"
    assert "steps.release.outputs.skip != 'true'" in steps[-1]["if"]
    assert "npm run verify" in indexed["build"]["run"]
    assert indexed["receipt"]["run"] == "node scripts/deploy-receipt.mjs"
