"""AI-v1 publication preserves qualification provenance and aggregate sensors."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import census_ai_v1 as census


def _raw_row(repo_id, name, description, stars=1_000, topics=None):
    return {
        "id": repo_id,
        "full_name": f"systems/{name}",
        "stargazers_count": stars,
        "created_at": "2020-01-01T00:00:00Z",
        "pushed_at": "2026-08-03T00:00:00Z",
        "language": "Python",
        "description": description,
        "topics": topics or [],
        "license": "MIT",
    }


def _deep_row(row, *, readme="", manifests=None):
    return {
        "full_name": row["full_name"],
        "id": row["id"],
        "isFork": False,
        "isArchived": False,
        "license": "MIT",
        "language": "Python",
        "releases": 1,
        "commit_oid": f"oid-{row['id']}",
        "commits365": 1,
        "commits90": 1,
        "readme": readme,
        "manifests": manifests or {},
    }


def _emit_artifacts(tmp_path, monkeypatch):
    month_dir = tmp_path / "2026-08"
    month_dir.mkdir()
    description = "Inference server for model workloads"
    readme = "An AI assistant application."
    dependency_line = "torch>=2.0  # runtime framework"
    rows = [
        _raw_row(101, "serving-core", description, stars=1_004),
        _raw_row(102, "application-core", "General purpose software", stars=1_003),
        _raw_row(103, "training-core", "General purpose software", stars=1_002),
        _raw_row(104, "vision-core", "OCR pipeline", stars=1_001),
        _raw_row(105, "awesome-index", "AI assistant index", stars=1_000),
    ]
    deep = [
        _deep_row(rows[0]),
        _deep_row(rows[1], readme=readme),
        _deep_row(
            rows[2], manifests={"requirements.txt": dependency_line + "\n"}
        ),
        _deep_row(rows[3]),
    ]
    (month_dir / "raw-500plus-complete.json").write_text(
        json.dumps({"collected": len(rows)})
    )
    (month_dir / "raw-500plus.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )
    (month_dir / "deepcheck.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in deep)
    )
    monkeypatch.setattr(census, "registry_ids", lambda: {})
    monkeypatch.setattr(
        census, "previous_qualification_dates", lambda _month_dir: {102: "2026-07-01"}
    )

    census.emit(month_dir)
    manifest = json.loads((month_dir / "pending-manifest.json").read_text())
    run = json.loads((month_dir / "census-run.json").read_text())
    return manifest, run, description, readme, dependency_line


def test_members_anchor_qualification_text_date_and_executor(tmp_path, monkeypatch):
    manifest, run, description, readme, dependency_line = _emit_artifacts(
        tmp_path, monkeypatch
    )
    members = {member["repo_id"]: member for member in manifest["members"]}
    census_date = run["run_at"][:10]

    assert members[101]["qualifying_text_sha256"] == census.sha256_text(description)
    assert members[102]["qualifying_text_sha256"] == census.sha256_text(readme)
    assert members[103]["qualifying_text_sha256"] == census.sha256_text(
        dependency_line
    )
    assert members[102]["first_qualified_on"] == "2026-07-01"
    assert members[101]["first_qualified_on"] == census_date
    assert "pre-qualification history" in run["qualification_history_note"]
    assert "always declared an AI identity" in run["qualification_history_note"]

    executor_hash = hashlib.sha256(census.EXECUTOR_SRC.read_bytes()).hexdigest()
    for artifact in (manifest, run):
        assert artifact["executor_sha256"] == executor_hash
        assert artifact["governance_act_sha256"] == census.sha256(census.ACT)
        assert artifact["scope_module_sha256"] == census.sha256(census.SCOPE_SRC)


def test_strata_are_frozen_mechanical_and_published(tmp_path, monkeypatch):
    manifest, run, *_ = _emit_artifacts(tmp_path, monkeypatch)
    members = {member["repo_id"]: member for member in manifest["members"]}

    assert members[101]["stratum"] == "model-infrastructure"
    assert members[102]["stratum"] == "declared-application"
    assert members[103]["stratum"] == "model-infrastructure"
    assert members[104]["stratum"] == "other-declared"
    assert run["strata_counts"] == {
        "model-infrastructure": 2,
        "declared-application": 1,
        "other-declared": 1,
    }
    with pytest.raises(TypeError):
        census.STRATUM_BY_SIGNAL["new-signal"] = "other-declared"


def test_channel_attribution_splits_all_and_new_qualifications(tmp_path, monkeypatch):
    _, run, *_ = _emit_artifacts(tmp_path, monkeypatch)

    assert run["channel_attribution"] == {
        "all_admitted": {
            "storefront": 2,
            "readme": 1,
            "manifest": 1,
            "weak-topic+second": 0,
        },
        "first_qualified_on_this_census": {
            "storefront": 2,
            "readme": 0,
            "manifest": 1,
            "weak-topic+second": 0,
        },
    }
    every_channel = [
        {"admitted_by": channel, "first_qualified_on": "2026-08-03"}
        for channel in census.CHANNELS
    ]
    split = census.channel_attribution(every_channel, "2026-08-03")
    assert split["all_admitted"] == dict.fromkeys(census.CHANNELS, 1)
    assert split["first_qualified_on_this_census"] == dict.fromkeys(
        census.CHANNELS, 1
    )


def test_blocklist_rows_and_tokens_are_counted_without_names(tmp_path, monkeypatch):
    _, run, *_ = _emit_artifacts(tmp_path, monkeypatch)

    assert run["aggregate"]["blocked_nonsystem"] == 1
    assert run["blocklist_token_histogram"] == {"awesome": 1}
    assert "awesome-index" not in json.dumps(run["blocklist_token_histogram"])

    rows = [
        _raw_row(201, "tutorial-model", None),
        _raw_row(202, "runtime", "An awesome AI assistant"),
        _raw_row(203, "ordinary", None),
    ]
    histogram = {}
    candidates = census.candidates_of(rows, histogram)
    assert [row["id"] for row in candidates] == [203]
    assert histogram == {"tutorial": 1, "awesome": 1}
