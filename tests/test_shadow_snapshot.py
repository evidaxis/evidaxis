"""Shadow snapshots retain only the policy fields and fail closed on short bands."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import census_ai_v1 as census
import shadow_snapshot as shadow


def test_snapshot_bytes_have_only_the_shadow_projection(tmp_path, monkeypatch):
    observed_at = "2026-08-03T05:43:00Z"

    def fake_sweep(lo, hi, out_path, bands_path, project):
        assert (lo, hi) == (200, 499)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        source = {
            "id": 42,
            "stargazers_count": 321,
            "created_at": "2020-01-01T00:00:00Z",
            "description": "must not survive",
            "topics": ["must-not-survive"],
        }
        out_path.write_text(json.dumps(project(source)) + "\n")
        bands_path.write_text(json.dumps({
            "lo": 200, "hi": 499, "total": 1, "collected": 1,
            "index_drift": 0, "fresh": 1, "done": True,
        }) + "\n")
        (out_path.parent / f"{out_path.stem}-complete.json").write_text(
            json.dumps({"bar_lo": 200, "bar_hi": 499, "universe": 1})
        )

    monkeypatch.setattr(shadow, "_utc_timestamp", lambda: observed_at)
    monkeypatch.setattr(shadow, "census_sweep", fake_sweep)
    snapshot = shadow.collect_snapshot(tmp_path, "2026-08-03")

    stored = json.loads(snapshot.read_text())
    assert stored == {"id": 42, "stars": 321, "observed_at": observed_at}
    assert set(stored) == {"id", "stars", "observed_at"}
    expected_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert snapshot.with_suffix(".sha256").read_text() == (
        f"{expected_hash}  2026-08-03.jsonl\n"
    )

    monkeypatch.setattr(
        shadow,
        "census_sweep",
        lambda *args, **kwargs: pytest.fail("same-date rerun must be idempotent"),
    )
    assert shadow.collect_snapshot(tmp_path, "2026-08-03") == snapshot


def test_short_band_retries_three_times_then_raises(tmp_path, monkeypatch):
    calls = 0
    item = {
        "id": 7,
        "full_name": None,
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
        return {"total_count": 2, "incomplete_results": False, "items": [item]}

    monkeypatch.setattr(census, "gh_search", short_search)
    monkeypatch.setattr(census.time, "sleep", lambda _seconds: None)
    raw_path = tmp_path / "repos.jsonl"
    bands_path = tmp_path / "bands.jsonl"

    with pytest.raises(RuntimeError, match="short by 1 after 4 attempts"):
        census.sweep(
            200,
            200,
            raw_path,
            bands_path,
            project=lambda row: shadow.shadow_record(
                row, "2026-08-03T05:43:00Z"
            ),
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
        project=lambda row: shadow.shadow_record(row, "2026-08-03T05:43:00Z"),
    )

    band = json.loads(bands_path.read_text())
    assert band["done"] is True
    assert band["index_drift"] == 1
    assert len(raw_path.read_text().splitlines()) == 2
