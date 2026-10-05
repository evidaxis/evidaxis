import json
from unittest.mock import Mock

import pytest

from collectors import preflight


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("live network is forbidden in preflight tests")
    monkeypatch.setattr(preflight.gh_graphql.gh_http, "request", forbidden)
    monkeypatch.setattr(preflight.gh_auth, "token", lambda: "mock-token")


def entry(name, kind="Organization", repo_id=1):
    return {"full_name": name, "owner_type": kind, "repo_id": repo_id}


def test_all_moves_departures_and_errors_reported_together():
    repos = ["gone/a", "person/a", "person/b", "private/a", "reused/a", "live/a"]
    registry = {r: entry(r, "User") for r in repos}
    responses = [preflight.owner_classify.RepositoryHTTPError("gone/a", 404),
                 entry("org/a"), entry("org/b"),
                 preflight.owner_classify.RepositoryHTTPError("private/a", 403),
                 entry("reused/a", repo_id=2), entry("live/a", "User")]
    fetch = Mock(side_effect=responses)
    result = preflight.inspect(repos, registry, "mock", fetch, "2026-10-05")
    assert fetch.call_count == len(repos) == result["checked"]
    assert result["departed"] == [{"date": "2026-10-05", "github_repo": "gone/a", "github_status": 404}]
    assert [m["github_repo"] for m in result["moves"]] == ["person/a", "person/b", "reused/a"]
    assert [e["github_repo"] for e in result["errors"]] == ["private/a"]


def test_confirmed_alias_and_case_change_are_not_new_moves():
    result = preflight.inspect(["old/tool"], {"old/tool": entry("org/tool")}, "mock",
                               Mock(return_value=entry("Org/Tool")), "2026-10-05")
    assert not any(result[k] for k in ("moves", "departed", "errors"))


@pytest.mark.parametrize("status", [404, 410, 451])
def test_departure_preserves_the_observed_http_code(status):
    fetch = Mock(side_effect=preflight.owner_classify.RepositoryHTTPError("gone/tool", status))
    result = preflight.inspect(["gone/tool"], {}, "mock", fetch, "2026-10-05")
    assert result["departed"][0]["github_status"] == status


def test_transport_failure_does_not_hide_a_later_move():
    fetch = Mock(side_effect=[OSError("mock timeout"), entry("new/tool")])
    result = preflight.inspect(["broken/tool", "old/tool"], {}, "mock", fetch, "2026-10-05")
    assert len(result["errors"]) == len(result["moves"]) == 1
    assert result["departed"] == []


def test_clean_cli_is_green_without_mutating_inputs(monkeypatch, tmp_path):
    seeds = tmp_path / "seeds.json"
    owners = tmp_path / "owners.json"
    seeds.write_text(json.dumps({"verticals": {"test": {"entities": [{"github_repo": "org/tool"}]}}}))
    owners.write_text(json.dumps({"repos": {"org/tool": entry("org/tool")}}))
    before = seeds.read_bytes(), owners.read_bytes()
    factory = Mock(return_value=Mock(return_value=entry("org/tool")))
    monkeypatch.setattr(preflight.owner_classify, "graphql_fetcher", factory)
    output = tmp_path / "report.json"
    assert preflight.main(["--seeds", str(seeds), "--owners", str(owners), "--output", str(output)]) == 0
    factory.assert_called_once_with(["org/tool"], fresh=True)
    assert json.loads(output.read_text())["checked"] == 1
    assert (seeds.read_bytes(), owners.read_bytes()) == before


def test_cli_single_fresh_graphql_pass_and_rest_only_for_nulls(monkeypatch, tmp_path):
    repos = ["gone/tool", "old/a", "old/b", "live/tool"]
    seeds = tmp_path / "seeds.json"
    seeds.write_text(json.dumps({"verticals": {"test": {"entities": [
        {"github_repo": r} for r in repos
    ]}}}))
    owners = tmp_path / "owners.json"
    owners.write_text(json.dumps({"repos": {r: entry(r) for r in repos}}))
    batch = Mock(return_value={
        "gone/tool": None,
        **{r: {"nameWithOwner": name, "databaseId": 1, "owner_type": "Organization"}
           for r, name in zip(repos[1:], ["new/a", "new/b", "live/tool"], strict=True)},
    })
    monkeypatch.setattr(preflight.gh_graphql, "prefetch", batch)
    rest = Mock(side_effect=preflight.owner_classify.RepositoryHTTPError("gone/tool", 404))
    monkeypatch.setattr(preflight.owner_classify, "_rest_classification", rest)
    output = tmp_path / "preflight.json"
    assert preflight.main(["--seeds", str(seeds), "--owners", str(owners), "--output", str(output)]) == 1
    batch.assert_called_once_with(repos, fresh=True)
    rest.assert_called_once_with("gone/tool")
    report = json.loads(output.read_text())
    assert report["checked"] == 4
    assert len(report["moves"]) == 2
    assert len(report["departed"]) == 1
    assert not report["errors"]


def test_fresh_batch_does_not_reuse_stale_success(monkeypatch, tmp_path):
    gh = preflight.gh_graphql
    cache = tmp_path / "repo_meta.json"
    gh.save_cache({"gone/tool": {"nameWithOwner": "gone/tool"}}, cache)
    batch = Mock(return_value={"gone/tool": None})
    monkeypatch.setattr(gh, "fetch_batch", batch)
    assert gh.prefetch(["gone/tool"], cache, fresh=True) == {"gone/tool": None}
    batch.assert_called_once_with(["gone/tool"])


def test_weekly_preflight_precedes_expensive_collection():
    workflow = (preflight.HERE.parent / ".github/workflows/weekly-snapshot.yml").read_text()
    assert workflow.index("python3 collectors/preflight.py") < workflow.index("EVX_PASS: warm")
    assert "run: python3 collectors/gh_graphql.py" not in workflow
