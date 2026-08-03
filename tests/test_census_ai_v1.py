"""AI-v1 publication preserves qualification provenance and aggregate sensors."""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
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
        census, "previous_qualification_dates", lambda _month_dir: {104: "2026-07-01"}
    )

    census.emit(month_dir)
    manifest = json.loads((month_dir / "pending-manifest.json").read_text())
    run = json.loads((month_dir / "census-run.json").read_text())
    return manifest, run, description, readme, dependency_line


def test_members_anchor_qualification_text_date_and_executor(tmp_path, monkeypatch):
    manifest, run, description, *_ = _emit_artifacts(
        tmp_path, monkeypatch
    )
    members = {member["repo_id"]: member for member in manifest["members"]}
    census_date = run["run_at"][:10]

    assert members[101]["qualifying_text_sha256"] == census.sha256_text(
        f"serving-core {description}"
    )
    assert members[104]["qualifying_text_sha256"] == census.sha256_text(
        "vision-core OCR pipeline"
    )
    assert members[104]["first_qualified_on"] == "2026-07-01"
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
    assert members[104]["stratum"] == "other-declared"
    assert run["strata_counts"] == {
        "model-infrastructure": 1,
        "declared-application": 0,
        "other-declared": 1,
    }
    with pytest.raises(TypeError):
        census.STRATUM_BY_SIGNAL["new-signal"] = "other-declared"


def test_channel_attribution_splits_all_and_new_qualifications(tmp_path, monkeypatch):
    _, run, *_ = _emit_artifacts(tmp_path, monkeypatch)

    all_admitted = run["channel_attribution"]["all_admitted"]
    first_qualified = run["channel_attribution"][
        "first_qualified_on_this_census"
    ]
    assert all_admitted["storefront"] == 2
    assert sum(all_admitted.values()) == 2
    assert first_qualified["storefront"] == 1
    assert sum(first_qualified.values()) == 1
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


class _ReadmeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def test_readme_prefix_tries_extended_names_and_keeps_ranged_request(monkeypatch):
    requests = []

    def open_readme(request, timeout):
        requests.append(request)
        if request.full_url.endswith("/docs/README.md"):
            return _ReadmeResponse(b"AI system")
        raise urllib.error.HTTPError(request.full_url, 404, "missing", {}, None)

    monkeypatch.setattr(census.urllib.request, "urlopen", open_readme)

    assert census.readme_prefix("group/project") == "AI system"
    assert [request.full_url.rsplit("/HEAD/", 1)[1] for request in requests] == list(
        census.README_NAMES
    )
    assert {request.get_header("Range") for request in requests} == {
        f"bytes=0-{census.README_PREFIX}"
    }


def test_readme_prefix_rejects_non_utf8_text(monkeypatch):
    monkeypatch.setattr(
        census.urllib.request,
        "urlopen",
        lambda _request, timeout: _ReadmeResponse(b"\xff\xfe"),
    )

    assert census.readme_prefix("group/project") == ""


def test_deepcheck_records_repository_without_default_branch(tmp_path, monkeypatch):
    node = {
        "databaseId": 7,
        "nameWithOwner": "group/empty",
        "isFork": False,
        "isArchived": False,
        "licenseInfo": {"spdxId": None},
        "primaryLanguage": None,
        "defaultBranchRef": None,
        "releases": {"totalCount": 0},
    }
    monkeypatch.setattr(census, "gh_graphql", lambda _query: ({"r0": node}, True))
    monkeypatch.setattr(
        census, "readme_batch", lambda names: dict.fromkeys(names, "")
    )
    monkeypatch.setattr(census.time, "sleep", lambda _seconds: None)
    output = tmp_path / "deepcheck.jsonl"

    census.deepcheck([{"id": 7, "full_name": "group/empty"}], output)

    recorded = json.loads(output.read_text())
    assert recorded["no_default_branch"] is True
    assert recorded["commit_oid"] is None


def test_stock_census_flag_stamps_intent_and_empty_repo_counter(
        tmp_path, monkeypatch):
    monkeypatch.setattr(census, "REPO", tmp_path)

    def fake_emit(month_dir):
        (month_dir / "pending-manifest.json").write_text(json.dumps({
            "wave": "forward",
            "members": [{"repo_id": 7, "wave": "forward"}],
        }))
        (month_dir / "census-run.json").write_text(json.dumps({
            "aggregate": {"no_velocity": 1},
            "pending_manifest_sha256": "stale",
        }))
        (month_dir / "deepcheck.jsonl").write_text(
            json.dumps({"id": 7, "no_default_branch": True}) + "\n"
        )

    monkeypatch.setattr(census, "emit", fake_emit)
    monkeypatch.setattr(
        sys,
        "argv",
        ["census_ai_v1.py", "emit", "--month", "2026-09", "--stock-census"],
    )

    assert census.main() == 0

    month_dir = tmp_path / "data" / "census" / "2026-09"
    manifest = json.loads((month_dir / "pending-manifest.json").read_text())
    run = json.loads((month_dir / "census-run.json").read_text())
    assert manifest["stock_census"] is True
    assert manifest["wave"] == "backlog"
    assert manifest["members"][0]["wave"] == "backlog"
    assert run["stock_census"] is True
    assert run["activation_wave"] == "backlog"
    assert run["aggregate"]["no_default_branch"] == 1
    assert run["pending_manifest_sha256"] == census.sha256(
        month_dir / "pending-manifest.json"
    )
    assert (month_dir / "census-run.sha256").read_text() == (
        census.sha256(month_dir / "census-run.json") + "  census-run.json\n"
    )


def test_dead_channel_is_retained_only_for_historical_artifacts():
    assert "weak-topic+second" in census.CHANNELS
    table_rows = [
        line for line in census.ACT.read_text().splitlines()
        if line.startswith("|")
    ]
    assert not [line for line in table_rows if "weak-topic+second" in line]


def test_reemit_never_unpublishes_an_activation(tmp_path, monkeypatch):
    """A census may recompute who QUALIFIES; it may never un-publish history.

    Measured 2026-08-03: the first tranche marked ten members `activated`, and a
    re-emit an hour later - run for an unrelated fix - regenerated the manifest
    and wiped those marks. The next weekly tranche would have re-selected the
    same ten heads, applied zero because they are already members, and the
    backlog would never have drained. An adversarial review had already found
    that failure by a different route; regeneration reopened it.
    """
    import census_ai_v1 as census

    month_dir = tmp_path / "2026-08"
    month_dir.mkdir(parents=True)
    (month_dir / "pending-manifest.json").write_text(json.dumps({
        "members": [
            {"repo_id": 1, "status": "activated", "activated_on": "2026-08-03"},
            {"repo_id": 2, "status": "pending"},
        ]}))

    carried = census.previous_activation(month_dir)
    assert carried[1]["status"] == "activated"
    assert carried[1]["activated_on"] == "2026-08-03"
    assert 2 not in carried, "pending is the default, not carried state"
