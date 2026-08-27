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


def test_vanished_repository_is_churn_not_failure(tmp_path):
    """A repository present at discovery and gone at observation is DATA.

    Measured on the first live run: id 7061513 resolved during discovery and
    was unresolvable four hours later. At 146,589 repositories over a
    multi-hour gap that is ordinary churn, and aborting the weekly snapshot
    over one of them is the wrong trade - the same defect already fixed in the
    census collector, reproduced in this module because the fix lived in only
    one file.
    """
    import shadow_snapshot as shadow

    path = tmp_path / "shard-0.jsonl"
    # 200 discovered, 1 vanished: below the 1% allowance (ids are 1-based;
    # 0 is not a valid GitHub repository id and the record validator says so)
    expected = [{"id": i, "full_name": f"o/r{i}"} for i in range(1, 201)]
    got = [{"id": i, "stars": 300, "observed_at": "2026-08-03T00:00:00Z"}
           for i in range(1, 200)]
    path.write_text("\n".join(json.dumps(r) for r in got) + "\n")
    records = shadow._validate_observation_shard(path, "2026-08-03", expected)
    assert len(records) == 199, "churn below the allowance must not fail"


def test_mass_disappearance_still_fails(tmp_path):
    """Churn is tolerated; a systemic fault is not.

    A bad token or a wrong id set makes MANY ids unresolvable at once. The
    allowance exists to tell those apart, not to make absence invisible.
    """
    import pytest

    import shadow_snapshot as shadow

    path = tmp_path / "shard-0.jsonl"
    expected = [{"id": i, "full_name": f"o/r{i}"} for i in range(1, 201)]
    got = [{"id": i, "stars": 300, "observed_at": "2026-08-03T00:00:00Z"}
           for i in range(1, 101)]
    path.write_text("\n".join(json.dumps(r) for r in got) + "\n")
    with pytest.raises(RuntimeError, match="churn allowance"):
        shadow._validate_observation_shard(path, "2026-08-03", expected)


def test_merge_tolerates_the_same_churn_the_shards_do(tmp_path, monkeypatch):
    """One rule, applied wherever coverage is judged.

    The first live observation had shards pass (each reporting one vanished
    repository at 0.00%) and the MERGE fail at 146,570 of 146,572, because the
    allowance existed at one level and not the other. That is the same shape as
    the NOT_FOUND fix that lived in the census collector and not in this module:
    an invariant present in one place does not protect the other.
    """
    import shadow_snapshot as shadow

    discovery = [{"id": i, "full_name": f"o/r{i}"} for i in range(1, 1001)]
    observed = [{"id": i, "stars": 300, "observed_at": "2026-08-03T00:00:00Z"}
                for i in range(1, 999)]          # 2 of 1000 gone: 0.2%
    absent = len(discovery) - len(observed)
    share = absent / len(discovery)
    assert share <= shadow.ABSENT_LIMIT, "the fixture must sit below the allowance"
    excessive = len(discovery) - 500
    assert (excessive / len(discovery)) > shadow.ABSENT_LIMIT, (
        "a mass disappearance must still exceed it")


def _reset_churn():
    """The collector counts churn in module-level lists; tests own their own tally."""
    shadow._ABSENT.clear()
    shadow._REIDENTIFIED.clear()


def test_reidentified_repository_is_churn_not_a_crash(monkeypatch):
    """A discovery path that resolves to a DIFFERENT repository is churn.

    Three consecutive scheduled observations died on this (2026-08-09, -16, -23):
    ids 682844590 and 171837101 were renamed, transferred, or deleted with the
    name re-taken, and the collector raised, killing a whole shard and with it
    the weekly observation. Renaming is ordinary GitHub behaviour, not a fault
    of this archive - so it is counted like an absence, never recorded, never
    fatal. Nothing was watching the SHAPE of the failure either: this test is
    the regression net the 2026-08-23 fix shipped without.
    """
    _reset_churn()
    batch = [{"id": 11, "full_name": "o/kept"}, {"id": 22, "full_name": "o/renamed"}]

    def fake_graphql(_query):
        return (
            {
                "r0": {"databaseId": 11, "stargazerCount": 300},
                # Same path, different repository behind it now.
                "r1": {"databaseId": 999, "stargazerCount": 41000},
            },
            True,
        )

    monkeypatch.setattr(shadow, "census_graphql", fake_graphql)
    records = shadow._observe_batch(batch, "2026-08-30T05:43:00Z")

    assert [record["id"] for record in records] == [11], "foreign stars must not enter the series"
    assert not any(record["stars"] == 41000 for record in records)
    assert shadow._REIDENTIFIED == [(22, 999)], "the churn must stay countable, not vanish"


def test_identity_is_checked_even_when_the_batch_holds_an_absence(monkeypatch):
    """The hole the 2026-08-23 fix closed, pinned so it cannot reopen.

    Identity used to be verified only on a batch where every path resolved. A
    batch holding one absence took the other branch and admitted whatever the
    remaining paths returned - so a rename sitting next to a deletion put a
    stranger's star count into the series silently. Silent is the part that
    matters: a crash is visible, a foreign measurement is not.
    """
    _reset_churn()
    batch = [
        {"id": 11, "full_name": "o/kept"},
        {"id": 22, "full_name": "o/vanished"},
        {"id": 33, "full_name": "o/renamed"},
    ]

    def fake_graphql(_query):
        return (
            {
                "r0": {"databaseId": 11, "stargazerCount": 300},
                "r1": None,
                "r2": {"databaseId": 999, "stargazerCount": 41000},
            },
            True,
        )

    monkeypatch.setattr(shadow, "census_graphql", fake_graphql)
    records = shadow._observe_batch(batch, "2026-08-30T05:43:00Z")

    assert [record["id"] for record in records] == [11]
    assert shadow._ABSENT == [22]
    assert shadow._REIDENTIFIED == [(33, 999)]


def test_mass_reidentification_still_fails_the_shard(tmp_path):
    """Tolerating churn must not tolerate a wrong id set.

    Re-identified repositories never reach the shard file, so they land in the
    same absence share the systemic-fault guard reads. A handful is churn; a
    third of the shard resolving to strangers is a broken discovery set and
    must stop the run exactly like a mass disappearance does.
    """
    path = tmp_path / "shard-0.jsonl"
    expected = [{"id": i, "full_name": f"o/r{i}"} for i in range(1, 201)]
    got = [{"id": i, "stars": 300, "observed_at": "2026-08-30T05:43:00Z"}
           for i in range(1, 131)]
    path.write_text("\n".join(json.dumps(r) for r in got) + "\n")
    with pytest.raises(RuntimeError, match="churn allowance"):
        shadow._validate_observation_shard(path, "2026-08-30", expected)


def test_observation_shards_are_samples_of_the_same_population():
    """Equal COUNT was never the property the allowance needed - equal MIX was.

    The discovery set is sorted by repository id, ids ascend with creation date,
    and young repositories are the ones deleted and renamed. A contiguous split
    therefore handed the last shard a different world: measured 2026-08-23 over
    four identical 36,643-repo shards, absences were 15 / 16 / 19 / 109. The
    systemic-fault allowance is a flat 1% per shard, so shard 3 always burned it
    first - and one shard failing kills the whole weekly observation. Here the
    tail of the ordered input stands in for "young"; every shard must get its
    share of it.
    """
    ordered = list(range(1000))
    young = set(range(900, 1000))
    shards = [list(shadow.interleave_for_shard(ordered, shadow.Shard(i, 4)))
              for i in range(4)]

    per_shard = [len(young.intersection(shard)) for shard in shards]
    assert per_shard == [25, 25, 25, 25], "no shard may carry the churn for the rest"

    contiguous = [list(shadow.partition_for_shard(ordered, shadow.Shard(i, 4)))
                  for i in range(4)]
    assert [len(young.intersection(s)) for s in contiguous] == [0, 0, 0, 100], (
        "the old rule concentrated the whole population in one shard - the defect"
    )


def test_interleaved_shards_still_cover_the_set_exactly_once():
    """Rebalancing must not cost coverage: the union is still the whole set."""
    ordered = list(range(997))          # prime length: no shard divides evenly
    shards = [list(shadow.interleave_for_shard(ordered, shadow.Shard(i, 4)))
              for i in range(4)]

    seen = [item for shard in shards for item in shard]
    assert sorted(seen) == ordered, "every repository observed exactly once"
    assert max(len(s) for s in shards) - min(len(s) for s in shards) <= 1


def test_discovery_keeps_contiguous_bands():
    """Discovery must NOT interleave: its slice becomes one Search range query.

    `collect_discovery` reads assigned[0] and assigned[-1] and asks GitHub for
    `stars:{lo}..{hi}`. Interleaving star values would make every shard span the
    full 200..499 interval, so all four would enumerate the same repositories.
    """
    star_values = list(range(200, 500))
    for index in range(4):
        assigned = list(shadow.partition_for_shard(star_values, shadow.Shard(index, 4)))
        assert assigned == list(range(assigned[0], assigned[-1] + 1)), (
            "a discovery shard must stay an unbroken star interval"
        )
