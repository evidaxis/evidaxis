import json

from scripts import rehearsal_report as report


def snapshot(day, *ids):
    return {"snapshot_date": day, "methodology_version": "m5", "entities": [{"entity_id": value} for value in ids]}


def test_report_counts_departures_cap_methodology_and_durations():
    current, previous = snapshot("2026-10-24", "a", "c", "d"), snapshot("2026-10-17", "a", "b")
    jobs = [{"steps": [{"name": "Collect", "conclusion": "success", "started_at": "2026-10-21T02:17:00Z",
                        "completed_at": "2026-10-21T05:17:12Z"}, {"name": "Still running"}]}]
    result = report.build_report(current, previous, [{}] * 63, 6300, jobs)
    assert result == {"release_date": "2026-10-24", "previous_date": "2026-10-17", "methodology_version": "m5",
                      "systems": 3, "previous_systems": 2, "delta": 1, "missing_since_previous": 1,
                      "departures": 63, "departure_cap": 63, "within_cap": True,
                      "steps": [{"step": "Collect", "conclusion": "success", "seconds": 10812.0}]}
    assert "systems 3 vs 2 (+1)" in report.summary(result)
    assert "departures 63/63; cap PASS" in report.summary(result)
    small = report.build_report(current, previous, [{}] * 26, 100, [])
    assert small["departure_cap"] == 25 and not small["within_cap"]
    assert "cap FAIL" in report.summary(small)


def test_report_artifact_and_step_summary_use_previous_snapshot(tmp_path, monkeypatch):
    data, output = tmp_path / "data", tmp_path / "summary"
    output.mkdir()
    for day in ["2026-10-10", "2026-10-17", "2026-10-24", "2026-10-31"]:
        folder = data / "snapshots" / day
        folder.mkdir(parents=True)
        (folder / "snapshot.json").write_text(json.dumps(snapshot(day, "a")))
    (output / "summary-graphql.json").write_text(json.dumps({"repos": 100, "departed": []}))
    (output / "jobs.json").write_text('{"jobs": []}')
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "step-summary"))
    assert report.main(["--date", "2026-10-24", "--data-dir", str(data), "--summary-dir", str(output)]) == 0
    actual = json.loads((output / "rehearsal-report.json").read_text())
    assert actual["previous_date"] == "2026-10-17"
    assert "Rehearsal 2026-10-24: m5" in (tmp_path / "step-summary").read_text()


def test_failed_capture_leaves_incomplete_report(tmp_path):
    assert report.main(["--date", "2026-10-24", "--data-dir", str(tmp_path), "--summary-dir", str(tmp_path)]) == 1
    assert json.loads((tmp_path / "rehearsal-report.json").read_text())["complete"] is False
