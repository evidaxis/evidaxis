"""A failed integrity step is named in the log with a run link; CI sends no Telegram (2026-10-29)."""
import json
import os
from pathlib import Path
import subprocess

import yaml


def test_archive_failure_step_names_failed_steps_without_telegram():
    workflow = yaml.safe_load(Path(".github/workflows/archive-integrity.yml").read_text())
    steps = workflow["jobs"]["verify"]["steps"]
    alert = steps[-1]
    assert alert["if"] == "failure()"
    assert all("id" in step for step in steps[:-1])
    assert alert["env"]["INTEGRITY_STEPS"] == "${{ toJSON(steps) }}"
    assert alert["env"]["RUN_URL"] == "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
    # The red run is the alarm; the keeper's Mac sentinel reads it. No bot token in CI.
    assert "TELEGRAM_BOT_TOKEN" not in alert["env"] and "ALERT_CHAT_ID" not in alert["env"]
    assert "api.telegram.org" not in alert["run"]

    script = alert["run"].split("<<'JS'\n", 1)[1].rsplit("\nJS", 1)[0]
    result = subprocess.run(
        ["node", "--input-type=module", "-"],
        input=script, text=True, capture_output=True, check=False,
        env={**os.environ,
             "RUN_URL": "https://github.com/evidaxis/evidaxis/actions/runs/123",
             "INTEGRITY_STEPS": json.dumps({"snapshot_checksums": {"outcome": "failure"},
                                            "checkout": {"outcome": "success"},
                                            "genesis_bytes": {"outcome": "skipped"}})},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == (
        "::error title=archive-integrity failed::Failed steps: snapshot_checksums "
        "https://github.com/evidaxis/evidaxis/actions/runs/123"
    )
