from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from scripts import release_guard as guard

NOW = datetime(2026, 10, 17, 2, 17, tzinfo=timezone.utc)


def test_current_workflow_names_manual_defaults_and_schedule_as_routers():
    workflow = yaml.safe_load(Path(".github/workflows/weekly-snapshot.yml").read_text())
    # Both events have empty date inputs; bare `weekly-snapshot` titles are legacy.
    assert workflow["run-name"] == "weekly ${{ inputs.mode || 'release' }} ${{ inputs.release_date || 'resolve-date' }}"
    triggers = workflow[True]  # PyYAML's YAML 1.1 parser reads the Actions `on` key as True.
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["mode"]["default"] == "release"
    assert inputs["release_date"]["default"] == ""
    assert triggers["schedule"] == [{"cron": "17 6 * * 6"}]


def test_default_date_uses_last_saturday_in_utc():
    assert guard.release_date("", "release", NOW) == "2026-10-17"
    assert guard.release_date("", "rehearsal", datetime.fromisoformat("2026-10-17T01:00:00+02:00")) == "2026-10-10"
    assert guard.release_date("", "release", datetime(2026, 10, 21, tzinfo=timezone.utc)) == "2026-10-17"


@pytest.mark.parametrize("value,mode", [
    ("2026-10-18", "release"), ("2026-02-30", "release"), ("20261017", "release"),
    ("2026-10-24", "release"), ("2026-10-17", "invalid"), ("2026-1-17", "release"),
])
def test_invalid_release_dates(value, mode):
    with pytest.raises(ValueError):
        guard.release_date(value, mode, NOW)


def test_rehearsal_may_target_future_saturday():
    assert guard.release_date("2026-10-24", "rehearsal", NOW) == "2026-10-24"
    assert guard.release_date("2026-10-10", "release", NOW) == "2026-10-10"


def test_archive_guard_including_real_2026_10_17(tmp_path):
    assert guard.already_exists(Path("data"), "2026-10-17", "release", [])
    (tmp_path / "snapshots/2026-10-17").mkdir(parents=True)
    assert guard.already_exists(tmp_path, "2026-10-17", "release", [])
    assert not guard.already_exists(tmp_path, "2026-10-17", "rehearsal", [])
    assert not guard.already_exists(tmp_path, "2026-10-24", "release", [])


def test_success_guard_is_exact_and_excludes_current_run(tmp_path):
    run = {"id": 1, "display_title": "weekly release 2026-10-17", "head_branch": "main", "conclusion": "success"}
    assert guard.already_exists(tmp_path, "2026-10-17", "release", [run], "2")
    for change in [{"display_title": "weekly rehearsal 2026-10-17"}, {"head_branch": "test"},
                   {"conclusion": "failure"}, {"display_title": "weekly release 2026-10-10"}, {"id": 2}]:
        assert not guard.already_exists(tmp_path, "2026-10-17", "release", [run | change], "2")


def test_guard_skips_archive_without_api_or_dispatch(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("MODE", "release")
    monkeypatch.setenv("INPUT_DATE", "2026-10-17")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setattr("sys.argv", ["release_guard.py", "--route"])
    monkeypatch.setattr(guard, "github_request", lambda *args: pytest.fail("archive must prevent API/dispatch"))
    guard.main()
    assert "уже есть" in capsys.readouterr().out
    assert "skip=true" in (tmp_path / "output").read_text()


def test_history_pagination_and_api_failure_are_closed(monkeypatch):
    pages = iter([{"workflow_runs": [{"id": 1}], "total_count": 2},
                  {"workflow_runs": [{"id": 2}], "total_count": 2}])
    monkeypatch.setattr(guard, "github_request", lambda path: next(pages))
    assert guard.successful_runs() == [{"id": 1}, {"id": 2}]
    monkeypatch.setattr(guard, "github_request", lambda path: {"workflow_runs": [], "total_count": 2})
    with pytest.raises(ValueError, match="incomplete"):
        guard.successful_runs()


def test_empty_date_routes_rehearsal_with_resolved_identity(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODE", "rehearsal")
    monkeypatch.setenv("INPUT_DATE", "")
    monkeypatch.setenv("GITHUB_REF_NAME", "ops/release-clock")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setattr("sys.argv", ["release_guard.py", "--route"])
    monkeypatch.setattr(guard, "release_date", lambda value, mode: "2026-10-17")
    calls = []
    monkeypatch.setattr(guard, "github_request", lambda *args: calls.append(args))
    guard.main()
    assert calls == [("actions/workflows/weekly-snapshot.yml/dispatches",
                      {"ref": "ops/release-clock", "inputs": {"mode": "rehearsal", "release_date": "2026-10-17"}})]
