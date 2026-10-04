"""False-zero commit_activity is an unresolved stats response, not a recorded zero.

No network: every GitHub body is a fake. Handles in this file are synthetic.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
sys.path.insert(0, str(REPO / "etl"))

import commit_activity_integrity as cai
import collect
import openalex_keyed_fetch as okf
import shadow_backfill

FALSE_ZERO = "example-org/false-zero-tool"
QUIET = "example-org/quiet-tool"
ACTIVE = "example-org/active-tool"
PROBE_DOWN = "example-org/probe-down-tool"
RUN_DATE = "2026-10-04"


@pytest.fixture(autouse=True)
def _clean_log():
    cai.reset_run_log()
    yield
    cai.reset_run_log()


def _weeks(n=52, total=0, start=1_700_000_000):
    return [{"week": start + i * 604800, "total": total} for i in range(n)]


def _since(payload):
    return datetime.fromtimestamp(payload[-12]["week"], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe_url(repo, payload):
    return f"https://api.github.com/repos/{repo}/commits?since={_since(payload)}&per_page=1"


# ---------------------------------------------------------------- helper


def test_all_zero_with_recent_commits_is_unresolved_not_a_recorded_zero():
    payload = _weeks()
    seen = []

    def fetch(url):
        seen.append(url)
        return [{"sha": "abc"}]

    assert cai.screen_commit_activity(FALSE_ZERO, payload, fetch, run_date=RUN_DATE) is None
    assert seen == [_probe_url(FALSE_ZERO, payload)]
    assert cai.RUN_LOG["refused"] == [{"repo": FALSE_ZERO, "run_date": RUN_DATE}]
    assert cai.RUN_LOG["probe_failed"] == 0
    assert set(cai.RUN_LOG["refused"][0]) == {"repo", "run_date"}


def test_all_zero_with_no_commits_keeps_the_zeros():
    payload = _weeks()

    def fetch(url):
        assert url == _probe_url(QUIET, payload)
        return []

    assert cai.screen_commit_activity(QUIET, payload, fetch, run_date=RUN_DATE) is payload
    assert cai.RUN_LOG["refused"] == []
    assert cai.RUN_LOG["probe_failed"] == 0


def test_nonzero_payload_is_untouched_and_makes_no_extra_call():
    payload = _weeks(total=0)
    payload[-1] = {"week": payload[-1]["week"], "total": 4}
    calls = []

    def fetch(url):
        calls.append(url)
        raise AssertionError("non-zero stats must not probe")

    assert cai.screen_commit_activity(ACTIVE, payload, fetch, run_date=RUN_DATE) is payload
    assert calls == []
    assert cai.RUN_LOG == {"refused": [], "probe_failed": 0}


def test_short_all_zero_series_is_not_a_twelve_week_window():
    payload = _weeks(n=11)
    assert cai.screen_commit_activity(QUIET, payload, lambda url: pytest.fail(url), run_date=RUN_DATE) is payload


@pytest.mark.parametrize("body", [None, "RATELIMIT", {"message": "no"}])
def test_probe_error_keeps_zeros_and_counts_the_failure(body):
    payload = _weeks()
    assert cai.screen_commit_activity(PROBE_DOWN, payload, lambda url: body, run_date=RUN_DATE) is payload
    assert cai.RUN_LOG["refused"] == []
    assert cai.RUN_LOG["probe_failed"] == 1


def test_probe_exception_keeps_zeros_and_counts_the_failure():
    payload = _weeks()

    def fetch(url):
        raise TimeoutError("down")

    assert cai.screen_commit_activity(PROBE_DOWN, payload, fetch, run_date=RUN_DATE) is payload
    assert cai.RUN_LOG["probe_failed"] == 1
    assert cai.RUN_LOG["refused"] == []


def test_missing_week_timestamp_counts_as_a_probe_failure_and_keeps_zeros():
    payload = [{"total": 0} for _ in range(12)]
    assert cai.screen_commit_activity(
        QUIET, payload, lambda url: pytest.fail(url), run_date=RUN_DATE) is payload
    assert cai.RUN_LOG["probe_failed"] == 1


# ---------------------------------------------------------------- weekly collector


def _run_wrapper(monkeypatch, tmp_path, repo, stats_body, commit_body):
    """Drive the production fetch layer (collectors/openalex_keyed_fetch.py), which the
    weekly pipeline installs as collect._get_json; etl/collect.py stays byte-frozen."""
    calls = []

    def fake_fetch(url, headers, tries, backoff_202=()):
        calls.append((url, tries))
        if url.endswith("/stats/commit_activity"):
            return "ok", stats_body
        if "/commits?" in url:
            body = commit_body(url)
            return ("ok", body) if body is not None else ("none", None)
        raise AssertionError(url)

    cached = {}
    monkeypatch.setattr(okf, "_fetch", fake_fetch)
    monkeypatch.setattr(okf, "_act_cache_get", lambda r: None)
    monkeypatch.setattr(okf, "_act_cache_put", lambda r, b: cached.__setitem__(r, b))
    monkeypatch.setenv("SNAPSHOT_DATE", RUN_DATE)
    okf._reset_run()
    url = f"https://api.github.com/repos/{repo}/stats/commit_activity"
    result = okf._github_get(url, collect.GH_HDR, 3)
    return result, calls, cached


def test_fetch_layer_refuses_a_false_zero_as_unresolved(monkeypatch, tmp_path):
    result, calls, cached = _run_wrapper(
        monkeypatch, tmp_path, FALSE_ZERO, _weeks(), lambda url: [{"sha": "abc"}])
    assert result is None  # frozen collect.py: `not act` -> declared gap, never a zero
    assert FALSE_ZERO not in cached
    assert [t for u, t in calls if "/commits?" in u] == [1]
    assert okf.RUN["act_none"] == 1
    assert cai.run_log_snapshot()["refused"] == [{"repo": FALSE_ZERO, "run_date": RUN_DATE}]


def test_fetch_layer_keeps_a_confirmed_zero(monkeypatch, tmp_path):
    zeros = _weeks()
    result, calls, cached = _run_wrapper(monkeypatch, tmp_path, QUIET, zeros, lambda url: [])
    assert result == zeros
    assert cached[QUIET] == zeros
    assert cai.run_log_snapshot()["refused"] == []


def test_fetch_layer_leaves_active_series_alone(monkeypatch, tmp_path):
    active = _weeks(total=4)
    result, calls, _ = _run_wrapper(
        monkeypatch, tmp_path, ACTIVE, active, lambda url: (_ for _ in ()).throw(AssertionError(url)))
    assert result == active
    assert not any("/commits?" in u for u, _ in calls)


def test_fetch_layer_keeps_zeros_when_the_probe_fails(monkeypatch, tmp_path, capsys):
    zeros = _weeks()
    result, _, _ = _run_wrapper(monkeypatch, tmp_path, PROBE_DOWN, zeros, lambda url: None)
    assert result == zeros
    assert cai.run_log_snapshot()["probe_failed"] == 1
    assert f"commit_activity probe failed for {PROBE_DOWN}; keeping the stats zeros" in capsys.readouterr().out


def test_frozen_collector_is_byte_identical_to_its_m2_state():
    frozen = (REPO / "etl/collect.py").read_bytes()
    assert b"commit_activity_integrity" not in frozen, "the false-zero check belongs to the fetch layer"


# ---------------------------------------------------------------- shadow backfill


def _run_backfill(monkeypatch, tmp_path, repo, commit_body):
    seeds = tmp_path / "seeds.json"
    id_map = tmp_path / "id_map.json"
    out = tmp_path / "backfill"
    seeds.write_text(json.dumps({"verticals": {"v": {"entities": [{"github_repo": repo}]}}}))
    id_map.write_text(json.dumps({repo: "e_TESTSYNTH1"}))
    monkeypatch.setattr(shadow_backfill, "SEEDS", seeds)
    monkeypatch.setattr(shadow_backfill, "ID_MAP", id_map)
    monkeypatch.setattr(shadow_backfill, "OUT_DIR", out)
    monkeypatch.setattr(shadow_backfill, "_token", lambda: "synthetic-token")
    monkeypatch.setattr(shadow_backfill.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", ["shadow_backfill"])
    seen = []

    def request(url, token):
        assert token == "synthetic-token"
        seen.append(url)
        if url.endswith("/stats/commit_activity"):
            return "ok", _weeks()
        if "/commits?" in url:
            return "ok", commit_body
        raise AssertionError(url)

    monkeypatch.setattr(shadow_backfill, "_request_json", request)
    assert shadow_backfill.main() == 0
    manifest = json.loads((out / "backfill_manifest.json").read_text())
    return manifest, out, seen


def test_backfill_refuses_a_false_zero_like_an_unresolved_stats_response(monkeypatch, tmp_path):
    manifest, out, seen = _run_backfill(monkeypatch, tmp_path, FALSE_ZERO, [{"sha": "abc"}])
    assert manifest["n_reconstructed"] == 0
    assert manifest["skipped"] == [{"repo": FALSE_ZERO, "reason": "no commit_activity (202/rate/absent)"}]
    assert manifest["commit_activity_false_zero"]["refused"] == [
        {"repo": FALSE_ZERO, "run_date": manifest["computed_at"][:10]}]
    assert manifest["commit_activity_false_zero"]["probe_failed"] == 0
    assert not (out / "e_TESTSYNTH1.backfill.jsonl").exists()
    assert any(url.endswith("/stats/commit_activity") for url in seen)
    assert any("/commits?" in url and "per_page=1" in url for url in seen)


def test_backfill_keeps_a_confirmed_zero(monkeypatch, tmp_path):
    manifest, out, _seen = _run_backfill(monkeypatch, tmp_path, QUIET, [])
    assert manifest["skipped"] == [{"repo": QUIET, "reason": "no nonzero weeks"}]
    assert manifest["commit_activity_false_zero"] == {"refused": [], "probe_failed": 0}
    assert not (out / "e_TESTSYNTH1.backfill.jsonl").exists()


# ---------------------------------------------------------------- weekly run summary


def test_capture_summary_counts_refused_false_zeros(tmp_path, monkeypatch):
    monkeypatch.setenv("EVX_GH_CACHE_DIR", str(tmp_path / "outside-cache"))
    monkeypatch.setenv("EVX_PASS", "capture")
    cai.RUN_LOG["refused"].append({"repo": FALSE_ZERO, "run_date": RUN_DATE})
    cai.RUN_LOG["probe_failed"] = 2
    okf.RUN.clear()
    okf.RUN.update({"pass": "capture", "repos": 1, "act_200": 1, "act_cache_hits": 0,
                    "act_202_final": 0, "act_none": 0, "meta_cache_hits": 0, "meta_rest": 0,
                    "started": 0, "warm_202": []})
    okf._write_summary()
    summary = json.loads((tmp_path / "outside-cache" / "summary-capture.json").read_text())
    assert summary["commit_activity_false_zero_refused"] == 1
    assert summary["commit_activity_probe_failed"] == 2


def test_reset_run_clears_a_stale_false_zero_count():
    cai.RUN_LOG["refused"].append({"repo": FALSE_ZERO, "run_date": RUN_DATE})
    cai.RUN_LOG["probe_failed"] = 4
    okf._reset_run()
    assert cai.RUN_LOG == {"refused": [], "probe_failed": 0}
