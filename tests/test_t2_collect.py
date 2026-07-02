"""t2_collect (daily Type-2 GitHub capture): fail-loud discipline.

HARD: no network. The single urllib chokepoint (_fetch / urlopen) is
monkeypatched. Table-driven around the 2026-07-02 findings: 401 must abort,
an empty/degraded capture must exit non-zero, a healthy capture exits 0 and
appends history.
"""
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))

import t2_collect


def _seed_repo(tmp_path, repos):
    (tmp_path / "etl").mkdir()
    seeds = {"verticals": {"v": {"entities": [{"github_repo": r} for r in repos]}}}
    (tmp_path / "etl" / "seeds.json").write_text(json.dumps(seeds))
    id_map = {r: f"e_{i:011d}" for i, r in enumerate(repos)}
    (tmp_path / "etl" / "id_map.json").write_text(json.dumps(id_map))
    return id_map


def _gh_body(**over):
    base = {"subscribers_count": 10, "open_issues_count": 5, "forks_count": 3,
            "network_count": 3, "stargazers_count": 100, "size": 42,
            "pushed_at": "2026-07-01T00:00:00Z", "owner": {"login": "someone"}}
    base.update(over)
    return json.dumps(base).encode()


def test_401_aborts_the_whole_capture(monkeypatch):
    def dead_token(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 401, "unauthorized", None, io.BytesIO(b""))
    monkeypatch.setattr(urllib.request, "urlopen", dead_token)
    with pytest.raises(RuntimeError, match="401"):
        t2_collect._fetch("https://api.github.com/repos/a/b", token="dead")


def test_total_failure_exits_nonzero_not_green(tmp_path, monkeypatch):
    _seed_repo(tmp_path, ["a/one", "b/two"])
    monkeypatch.setattr(t2_collect, "REPO", tmp_path)
    monkeypatch.setattr(t2_collect, "_fetch", lambda url, token, **kw: (500, b""))
    rc = t2_collect.capture()
    assert rc == 1
    manifests = list((tmp_path / "data" / "observations").glob("*/manifest.json"))
    assert manifests, "manifest must still be written for diagnostics"
    m = json.loads(manifests[0].read_text())
    assert m["degraded"] is True and m["entity_count"] == 0


def test_error_rate_above_floor_fails(tmp_path, monkeypatch):
    _seed_repo(tmp_path, ["a/one", "b/two", "c/three", "d/four"])
    calls = {"n": 0}

    def flaky(url, token, **kw):
        calls["n"] += 1
        return (500, b"") if calls["n"] == 1 else (200, _gh_body())

    monkeypatch.setattr(t2_collect, "REPO", tmp_path)
    monkeypatch.setattr(t2_collect, "_fetch", flaky)
    assert t2_collect.capture() == 1  # 1/4 = 25% > 20% floor


def test_healthy_capture_exits_zero_and_appends_history(tmp_path, monkeypatch):
    ids = _seed_repo(tmp_path, ["a/one", "b/two"])
    monkeypatch.setattr(t2_collect, "REPO", tmp_path)
    monkeypatch.setattr(t2_collect, "_fetch", lambda url, token, **kw: (200, _gh_body()))
    assert t2_collect.capture() == 0
    hist = tmp_path / "data" / "observations" / "history"
    assert sorted(p.name for p in hist.glob("*.t2.jsonl")) == \
        sorted(f"{eid}.t2.jsonl" for eid in ids.values())
    day = next((tmp_path / "data" / "observations").glob("*/observations.jsonl"))
    rows = [json.loads(line) for line in day.read_text().splitlines()]
    assert len(rows) == 2 and all(r["signals"]["watchers"]["value"] == 10 for r in rows)
    m = json.loads((day.parent / "manifest.json").read_text())
    assert m["degraded"] is False and m["error_rate"] == 0
