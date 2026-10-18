"""A failed integrity step reaches the existing Telegram transport with a run link."""
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml


@pytest.mark.parametrize("status", [200, 503])
def test_archive_failure_alert_uses_step_outcomes_and_run_url(tmp_path, status):
    workflow = yaml.safe_load(Path(".github/workflows/archive-integrity.yml").read_text())
    steps = workflow["jobs"]["verify"]["steps"]
    alert = steps[-1]
    assert alert["if"] == "failure()"
    assert all("id" in step for step in steps[:-1])
    assert alert["env"]["INTEGRITY_STEPS"] == "${{ toJSON(steps) }}"
    assert alert["env"]["TELEGRAM_BOT_TOKEN"] == "${{ secrets.TELEGRAM_BOT_TOKEN }}"
    assert alert["env"]["ALERT_CHAT_ID"] == "${{ secrets.ALERT_TG_CHAT_ID }}"
    assert alert["env"]["RUN_URL"] == "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"

    # Execute the workflow's actual inline program with fetch replaced before it
    # loads: this checks delivery and failure handling without sending a message.
    capture = tmp_path / "request.json"
    preload = tmp_path / "mock-telegram.mjs"
    preload.write_text(
        "import { writeFileSync } from 'node:fs';\n"
        "globalThis.fetch = async (url, options) => {\n"
        "  writeFileSync(process.env.CAPTURE, JSON.stringify({url, ...options}));\n"
        f"  return {{ ok: {str(status == 200).lower()}, status: {status} }};\n"
        "};\n"
    )
    script = alert["run"].split("<<'JS'\n", 1)[1].rsplit("\nJS", 1)[0]
    result = subprocess.run(
        ["node", "--import", str(preload), "--input-type=module", "-"],
        input=script, text=True, capture_output=True, check=False,
        env={**os.environ, "TELEGRAM_BOT_TOKEN": "test-token", "ALERT_CHAT_ID": "test-chat",
             "RUN_URL": "https://github.com/evidaxis/evidaxis/actions/runs/123",
             "INTEGRITY_STEPS": json.dumps({"snapshot_checksums": {"outcome": "failure"},
                                            "checkout": {"outcome": "success"},
                                            "genesis_bytes": {"outcome": "skipped"}}),
             "CAPTURE": str(capture)},
    )
    assert result.returncode == (0 if status == 200 else 1)
    request = json.loads(capture.read_text())
    assert request["url"] == "https://api.telegram.org/bottest-token/sendMessage"
    assert request["method"] == "POST"
    body = json.loads(request["body"])
    assert body == {
        "chat_id": "test-chat", "disable_web_page_preview": True,
        "text": "Evidaxis archive-integrity failed.\nFailed steps: snapshot_checksums\n"
                "https://github.com/evidaxis/evidaxis/actions/runs/123",
    }
    assert "test-token" not in result.stderr
