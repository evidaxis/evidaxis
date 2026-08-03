"""Shadow discovery and observation stay complete, private, and narrow."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import census_ai_v1 as census
import shadow_snapshot as shadow


def _write_discovery(shadow_repo: Path, records: list[dict]) -> Path:
    directory = shadow_repo / "discovery" / "2026-08"
    directory.mkdir(parents=True)
    shard = directory / "shard-0.jsonl"
    shard.write_text("".join(json.dumps(record) + "\n" for record in records))
    return shadow.merge_discovery(shadow_repo, "2026-08", 1)


def test_observe_without_discovery_fails_loudly(tmp_path):
    with pytest.raises(RuntimeError, match="shadow-discover workflow"):
        shadow.collect_observation(tmp_path, "2026-08-03", shadow.Shard(0, 4))
    assert not (tmp_path / "observations").exists()


def test_observation_storage_projection_has_no_extra_field(tmp_path, monkeypatch):
    observed_at = "2026-08-03T05:43:00Z"
    _write_discovery(
        tmp_path,
        [{"id": 42, "full_name": "organization/repository"}],
    )

    def fake_graphql(query):
        assert "nameWithOwner" not in query
        assert "description" not in query
        return {
            "r0": {
                "databaseId": 42,
                "stargazerCount": 321,
                "nameWithOwner": "must-not-survive",
                "description": "must-not-survive",
            }
        }, True

    monkeypatch.setattr(shadow, "_utc_timestamp", lambda: observed_at)
    monkeypatch.setattr(shadow, "census_graphql", fake_graphql)
    shard = shadow.collect_observation(
        tmp_path, "2026-08-03", shadow.Shard(0, 1)
    )

    stored = json.loads(shard.read_text())
    assert stored == {"id": 42, "stars": 321, "observed_at": observed_at}
    assert set(stored) == {"id", "stars", "observed_at"}

    snapshot = shadow.merge_observation(tmp_path, "2026-08-03", 1)
    assert snapshot.read_bytes() == shard.read_bytes()
    expected_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert snapshot.with_suffix(".sha256").read_text() == (
        f"{expected_hash}  snapshot.jsonl\n"
    )


def test_shard_partitioning_covers_every_input_exactly_once():
    inputs = list(range(137))
    partitions = [
        list(shadow.partition_for_shard(inputs, shadow.Shard(index, 8)))
        for index in range(8)
    ]
    counts = Counter(item for partition in partitions for item in partition)

    assert counts == Counter({item: 1 for item in inputs})
    assert max(map(len, partitions)) - min(map(len, partitions)) <= 1


def test_discovery_projects_search_rows_before_storage(tmp_path, monkeypatch):
    source = {
        "id": 42,
        "full_name": "organization/repository",
        "stargazers_count": 321,
        "created_at": "2020-01-01T00:00:00Z",
        "description": "must-not-survive",
        "topics": ["must-not-survive"],
    }

    monkeypatch.setattr(
        shadow,
        "census_search",
        lambda query, page: {
            "total_count": 1,
            "items": [source],
            "incomplete_results": False,
        },
    )

    def fake_sweep(lo, hi, out_path, bands_path, project):
        assert (lo, hi) == (200, 499)
        out_path.write_text(json.dumps(project(source)) + "\n")
        bands_path.write_text(
            json.dumps(
                {
                    "lo": lo,
                    "hi": hi,
                    "total": 1,
                    "collected": 1,
                    "index_drift": 0,
                    "fresh": 1,
                    "done": True,
                }
            )
            + "\n"
        )
        (out_path.parent / "repos-complete.json").write_text(
            json.dumps({"bar_lo": lo, "bar_hi": hi, "collected": 1})
        )

    monkeypatch.setattr(shadow, "census_sweep", fake_sweep)
    output = shadow.collect_discovery(tmp_path, "2026-08", shadow.Shard(0, 1))
    assert json.loads(output.read_text()) == {
        "id": 42,
        "full_name": "organization/repository",
    }


def test_discovery_merge_names_every_missing_shard(tmp_path):
    directory = tmp_path / "discovery" / "2026-08"
    directory.mkdir(parents=True)
    (directory / "shard-0.jsonl").write_text(
        json.dumps({"id": 42, "full_name": "organization/repository"}) + "\n"
    )

    with pytest.raises(RuntimeError, match=r"shard-1\.jsonl, shard-2\.jsonl"):
        shadow.merge_discovery(tmp_path, "2026-08", 3)


def test_short_band_beyond_tolerance_retries_then_raises(tmp_path, monkeypatch):
    calls = 0
    item = {
        "id": 7,
        "full_name": "organization/repository",
        "stargazers_count": 250,
        "created_at": "2020-01-01T00:00:00Z",
        "pushed_at": "2026-08-03T00:00:00Z",
        "language": "Python",
        "description": None,
        "topics": [],
        "license": None,
    }

    def short_search(query, page):
        nonlocal calls
        calls += 1
        assert query.startswith("stars:200..200")
        assert page == 1
        return {"total_count": 12, "incomplete_results": False, "items": [item]}

    monkeypatch.setattr(census, "gh_search", short_search)
    monkeypatch.setattr(census.time, "sleep", lambda _seconds: None)
    raw_path = tmp_path / "repos.jsonl"
    bands_path = tmp_path / "bands.jsonl"

    with pytest.raises(RuntimeError, match="short by 11 after 4 attempts"):
        census.sweep(
            200,
            200,
            raw_path,
            bands_path,
            project=lambda row: {"id": row["id"]},
        )

    assert calls == 4
    failures = [json.loads(line) for line in bands_path.read_text().splitlines()]
    assert [failure["attempt"] for failure in failures] == [1, 2, 3, 4]
    assert all(failure["done"] is False for failure in failures)
    assert all(failure["error"] == "collected < total_count" for failure in failures)
    assert not (tmp_path / "repos-complete.json").exists()


def test_surplus_is_accepted_and_recorded_as_index_drift(tmp_path, monkeypatch):
    items = [
        {"id": 7, "stargazers_count": 250},
        {"id": 8, "stargazers_count": 251},
    ]

    monkeypatch.setattr(
        census,
        "gh_search",
        lambda _query, _page: {
            "total_count": 1,
            "incomplete_results": False,
            "items": items,
        },
    )
    monkeypatch.setattr(census.time, "sleep", lambda _seconds: None)
    raw_path = tmp_path / "repos.jsonl"
    bands_path = tmp_path / "bands.jsonl"
    census.sweep(
        200,
        200,
        raw_path,
        bands_path,
        project=lambda row: {"id": row["id"]},
    )

    band = json.loads(bands_path.read_text())
    assert band["done"] is True
    assert band["index_drift"] == 1
    assert len(raw_path.read_text().splitlines()) == 2


def test_short_band_within_tolerance_is_recorded_not_retried(tmp_path, monkeypatch):
    item = {
        "id": 11,
        "full_name": "organization/repository",
        "stargazers_count": 300,
        "created_at": "2020-01-01T00:00:00Z",
        "pushed_at": "2026-08-03T00:00:00Z",
        "language": "Python",
        "description": None,
        "topics": [],
        "license": None,
    }
    calls = 0

    def one_short(_query, _page):
        nonlocal calls
        calls += 1
        return {"total_count": 2, "incomplete_results": False, "items": [item]}

    monkeypatch.setattr(census, "gh_search", one_short)
    monkeypatch.setattr(census.time, "sleep", lambda _seconds: None)
    raw_path, bands_path = tmp_path / "r.jsonl", tmp_path / "b.jsonl"
    census.sweep(300, 300, raw_path, bands_path)

    bands = [json.loads(line) for line in bands_path.read_text().splitlines()]
    done = [band for band in bands if band.get("done")]
    assert len(done) == 1
    assert done[0]["index_drift"] == -1
    assert calls <= 2
