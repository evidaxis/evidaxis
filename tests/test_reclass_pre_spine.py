"""Tests for etl/reclass_pre_spine.py — the PRE_INGEST_CONTRACT §1.2/§10 migration
that re-classes the v2 (pre-spine) baseline as PROVISIONAL (investor-grade audit baseline).

This migration is the audit hinge between the discarded v2 baseline (snapshot
90e607b982fa / methodology m1 / collect/2.x) and the genesis t=0 of the v3 spine.
It MUST be:
  - ADDITIVE     — only adds {provisional:true, spine_complete:false}, never rewrites
                   an existing value or touches a v3 (non-pre-spine) artifact's data.
  - IDEMPOTENT   — a second run is a strict no-op (the migration may be re-run safely).
  - CONSERVATIVE — anything matching ANY of the three pre-spine signals is flagged;
                   a clean v3 artifact is left alone.

No network (this module never does I/O over the wire). All writes go to tmp_path or a
monkeypatched DATA/REPO tree, never the real repo. conftest.py puts etl/ on sys.path
-> `import reclass_pre_spine`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import reclass_pre_spine as r


# ----------------------------------------------------------------- module constants

def test_flags_constant_exact():
    # the two flags this migration stamps — exact values are the audit contract
    assert r.FLAGS == {"provisional": True, "spine_complete": False}
    assert r.FLAGS["provisional"] is True
    assert r.FLAGS["spine_complete"] is False


# ----------------------------------------------------------------- is_pre_spine

# each of the three signals, in isolation, must classify as pre-spine
@pytest.mark.parametrize("obj", [
    {"fetcher_version": "collect/2.0"},          # collect/2.x signal
    {"fetcher_version": "collect/2.3.1"},
    {"fetcher_version": "collect/2"},            # bare "collect/2" still startswith
    {"methodology_version": "m1"},               # methodology m1 signal
    {"snapshot_id": "90e607b982fa"},             # the exact discarded baseline snapshot
    # any ONE signal is enough even with otherwise-v3-looking fields
    {"fetcher_version": "collect/3.0", "methodology_version": "m1"},
    {"fetcher_version": "collect/3.0", "snapshot_id": "90e607b982fa"},
])
def test_is_pre_spine_true(obj):
    assert r.is_pre_spine(obj) is True


# a clean v3 artifact, and near-misses on each signal, must NOT classify as pre-spine
@pytest.mark.parametrize("obj", [
    {"fetcher_version": "collect/3.0", "methodology_version": "m2", "snapshot_id": "deadbeef0000"},
    {"fetcher_version": "collect/3.1"},
    {"fetcher_version": "collect/30"},           # "collect/30" does NOT startswith "collect/2"
    {"fetcher_version": "collect/12"},
    {"methodology_version": "m10"},              # only exact "m1" matches, not prefix
    {"methodology_version": "m2"},
    {"snapshot_id": "90e607b982fb"},             # one hex char off -> not the baseline
    {"snapshot_id": "90E607B982FA"},             # case-sensitive exact match required
    {},                                          # empty dict -> defaults -> not pre-spine
    {"unrelated": "field"},
])
def test_is_pre_spine_false(obj):
    assert r.is_pre_spine(obj) is False


def test_is_pre_spine_coerces_non_str_versions():
    # fv/mv are str()-coerced before matching, so non-string values don't crash;
    # an int 2 stringifies to "2" which does NOT startswith "collect/2"
    assert r.is_pre_spine({"fetcher_version": 2}) is False
    assert r.is_pre_spine({"methodology_version": 1}) is False     # "1" != "m1"
    # snapshot_id is compared without coercion (==), so a non-matching type is False
    assert r.is_pre_spine({"snapshot_id": 90}) is False


# ----------------------------------------------------------------- patch_json

def _read(p: Path) -> dict:
    return json.loads(p.read_text())


def test_patch_json_flags_pre_spine_additively(tmp_path):
    p = tmp_path / "snapshot.json"
    p.write_text(json.dumps({"methodology_version": "m1", "kept": 7, "name": "x"}))
    assert r.patch_json(p) is True
    obj = _read(p)
    # the two flags are now present and correct
    assert obj["provisional"] is True
    assert obj["spine_complete"] is False
    # ADDITIVE: pre-existing keys/values are untouched
    assert obj["methodology_version"] == "m1"
    assert obj["kept"] == 7
    assert obj["name"] == "x"
    # file ends with exactly one trailing newline, pretty-printed (indent=2)
    text = p.read_text()
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert "\n  " in text                                          # indent=2 applied


def test_patch_json_idempotent(tmp_path):
    p = tmp_path / "snapshot.json"
    p.write_text(json.dumps({"snapshot_id": "90e607b982fa", "kept": 1}))
    assert r.patch_json(p) is True                                 # first run flags
    after_first = p.read_text()
    assert r.patch_json(p) is False                                # second run: no change
    assert p.read_text() == after_first                            # byte-for-byte identical
    # a third run is still a no-op
    assert r.patch_json(p) is False
    assert p.read_text() == after_first


def test_patch_json_non_pre_spine_returns_false_no_write(tmp_path):
    p = tmp_path / "v3.json"
    original = json.dumps({"fetcher_version": "collect/3.0", "methodology_version": "m2"})
    p.write_text(original)
    assert r.patch_json(p) is False
    assert p.read_text() == original                               # untouched, not re-serialized


@pytest.mark.parametrize("payload", ["[1, 2, 3]", '"a string"', "42", "true", "null"])
def test_patch_json_non_dict_returns_false(tmp_path, payload):
    # a non-dict top-level JSON value is never pre-spine and never crashes
    # (the isinstance check short-circuits before is_pre_spine touches .get)
    p = tmp_path / "x.json"
    p.write_text(payload)
    assert r.patch_json(p) is False
    assert p.read_text() == payload


def test_patch_json_reflags_partial_existing_flags(tmp_path):
    # a pre-spine obj carrying provisional:true but spine_complete:TRUE is NOT
    # considered fully flagged -> it gets corrected to spine_complete:false.
    p = tmp_path / "partial.json"
    p.write_text(json.dumps({"methodology_version": "m1", "provisional": True, "spine_complete": True}))
    assert r.patch_json(p) is True
    obj = _read(p)
    assert obj["provisional"] is True and obj["spine_complete"] is False


def test_patch_json_already_flagged_pre_spine_is_noop(tmp_path):
    # already fully flagged -> idempotent guard returns False without rewriting
    p = tmp_path / "done.json"
    original = json.dumps({"methodology_version": "m1", "provisional": True, "spine_complete": False})
    p.write_text(original)
    assert r.patch_json(p) is False
    assert p.read_text() == original


# ----------------------------------------------------------------- patch_jsonl

def test_patch_jsonl_flags_only_pre_spine_lines(tmp_path):
    p = tmp_path / "history.jsonl"
    lines = [
        json.dumps({"methodology_version": "m1", "id": 1}),        # pre-spine -> flag
        json.dumps({"fetcher_version": "collect/3.0", "id": 2}),   # v3 -> leave value alone
        json.dumps({"snapshot_id": "90e607b982fa", "id": 3}),      # pre-spine -> flag
    ]
    p.write_text("\n".join(lines) + "\n")
    changed = r.patch_jsonl(p)
    assert changed == 2                                            # two pre-spine lines flagged
    out = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    assert out[0]["provisional"] is True and out[0]["spine_complete"] is False
    assert out[0]["id"] == 1
    # the v3 line keeps its data and gains NO flags
    assert "provisional" not in out[1] and "spine_complete" not in out[1]
    assert out[1]["id"] == 2 and out[1]["fetcher_version"] == "collect/3.0"
    assert out[2]["provisional"] is True and out[2]["spine_complete"] is False
    assert out[2]["id"] == 3


def test_patch_jsonl_preserves_blank_lines_verbatim(tmp_path):
    p = tmp_path / "h.jsonl"
    # leading blank, a blank between records, trailing content; blanks must survive
    p.write_text("\n" + json.dumps({"methodology_version": "m1"}) + "\n\n"
                 + json.dumps({"fetcher_version": "collect/3.0"}) + "\n")
    changed = r.patch_jsonl(p)
    assert changed == 1
    raw = p.read_text().split("\n")
    # the all-whitespace/blank entries are appended unchanged (empty strings remain empty)
    assert raw[0] == ""                                            # leading blank preserved
    assert "" in raw[1:]                                           # an interior blank survives


def test_patch_jsonl_idempotent(tmp_path):
    p = tmp_path / "h.jsonl"
    p.write_text("\n".join([
        json.dumps({"methodology_version": "m1", "id": 1}),
        json.dumps({"fetcher_version": "collect/3.0", "id": 2}),
    ]) + "\n")
    assert r.patch_jsonl(p) == 1
    after_first = p.read_text()
    assert r.patch_jsonl(p) == 0                                   # second run: nothing changes
    assert p.read_text() == after_first                            # and file is byte-identical
    assert r.patch_jsonl(p) == 0                                   # still stable


def test_patch_jsonl_all_non_pre_spine_no_write(tmp_path):
    # zero pre-spine lines -> changed==0 -> file is NOT rewritten at all,
    # so even non-canonical whitespace in v3 lines is preserved verbatim.
    p = tmp_path / "h.jsonl"
    original = '{"fetcher_version":"collect/3.0","id":1}\n{"methodology_version":"m2","id":2}\n'
    p.write_text(original)
    assert r.patch_jsonl(p) == 0
    assert p.read_text() == original                              # untouched, compact form kept


def test_patch_jsonl_reserializes_non_pre_spine_lines_when_file_changes(tmp_path):
    """DOCUMENTED BEHAVIOR (not a values-bug, but a serialization side effect):
    when AT LEAST ONE line is flagged, the whole file is rewritten and EVERY
    surviving line is re-emitted through json.dumps. A non-pre-spine line written
    in compact form is therefore re-spaced (", "/": ") — its DATA is identical but
    its bytes change. Blank lines are exempt (appended verbatim)."""
    p = tmp_path / "h.jsonl"
    p.write_text('{"fetcher_version":"collect/3.0","id":1}\n'      # compact v3 line
                 + json.dumps({"methodology_version": "m1"}) + "\n")
    assert r.patch_jsonl(p) == 1
    out_lines = [ln for ln in p.read_text().splitlines() if ln.strip()]
    # the compact v3 line came back re-spaced (whitespace normalized) ...
    assert out_lines[0] == '{"fetcher_version": "collect/3.0", "id": 1}'
    # ... but its decoded value is byte-for-byte the same object (ADDITIVE-on-values)
    assert json.loads(out_lines[0]) == {"fetcher_version": "collect/3.0", "id": 1}


def test_patch_jsonl_partial_flagged_pre_spine_line_is_corrected(tmp_path):
    # a pre-spine line with provisional:true but spine_complete:true is re-flagged
    p = tmp_path / "h.jsonl"
    p.write_text(json.dumps({"methodology_version": "m1", "provisional": True, "spine_complete": True}) + "\n")
    assert r.patch_jsonl(p) == 1
    obj = json.loads(p.read_text().splitlines()[0])
    assert obj["provisional"] is True and obj["spine_complete"] is False


# ----------------------------------------------------------------- main()

@pytest.fixture
def fake_data_tree(tmp_path, monkeypatch):
    """Seed a throwaway data/ tree and redirect r.DATA / r.REPO at it, so main()
    walks the fake tree and writes only into tmp_path."""
    repo = tmp_path
    data = repo / "data"
    snap_dir = data / "snapshots" / "2026-06-29"
    snap_dir.mkdir(parents=True)
    hist_dir = data / "history"
    hist_dir.mkdir(parents=True)

    # pre-spine snapshot (the discarded baseline)
    (snap_dir / "snapshot.json").write_text(json.dumps(
        {"snapshot_id": "90e607b982fa", "methodology_version": "m1",
         "fetcher_version": "collect/2.0", "n": 5}))
    # latest.json pointing at the same pre-spine baseline
    (data / "latest.json").write_text(json.dumps(
        {"methodology_version": "m1", "fetcher_version": "collect/2.0"}))
    # history with mixed pre-spine and v3 lines + a blank line
    (hist_dir / "e_ABC.jsonl").write_text("\n".join([
        json.dumps({"methodology_version": "m1", "id": 1}),         # pre-spine
        "",                                                         # blank preserved
        json.dumps({"fetcher_version": "collect/3.0", "id": 2}),    # v3, left as-is
        json.dumps({"snapshot_id": "90e607b982fa", "id": 3}),       # pre-spine
    ]) + "\n")

    monkeypatch.setattr(r, "REPO", repo, raising=True)
    monkeypatch.setattr(r, "DATA", data, raising=True)
    return repo, data


def test_main_flags_pre_spine_artifacts(fake_data_tree, capsys):
    _, data = fake_data_tree
    r.main()

    # snapshot flagged
    snap = json.loads((data / "snapshots" / "2026-06-29" / "snapshot.json").read_text())
    assert snap["provisional"] is True and snap["spine_complete"] is False
    assert snap["n"] == 5                                          # additive

    # latest flagged
    latest = json.loads((data / "latest.json").read_text())
    assert latest["provisional"] is True and latest["spine_complete"] is False

    # history: the two pre-spine lines flagged, the v3 line left alone
    recs = [json.loads(ln) for ln in (data / "history" / "e_ABC.jsonl").read_text().splitlines() if ln.strip()]
    flagged = [rec for rec in recs if rec.get("provisional") is True]
    assert len(flagged) == 2
    v3 = next(rec for rec in recs if rec.get("id") == 2)
    assert "provisional" not in v3                                 # v3 line untouched

    out = capsys.readouterr().out
    assert "PRE-SPINE re-class:" in out
    # 3 artifacts touched: snapshot.json, latest.json, the one history file
    assert "3 artifact(s) flagged" in out


def test_main_idempotent_second_run_is_noop(fake_data_tree, capsys):
    _, data = fake_data_tree
    r.main()
    capsys.readouterr()                                            # drain first-run output

    # capture full tree state after the first run
    paths = sorted(data.rglob("*"))
    snapshot = {p: p.read_text() for p in paths if p.is_file()}

    r.main()                                                       # second run

    # every file is byte-for-byte unchanged
    for p, text in snapshot.items():
        assert p.read_text() == text, f"second run mutated {p}"

    out = capsys.readouterr().out
    assert "0 artifact(s) flagged" in out                         # nothing re-flagged


def test_main_no_data_dir_is_clean_noop(tmp_path, monkeypatch, capsys):
    # main() must not explode when there is no data/ tree at all (globs empty,
    # latest.json absent) — it just reports 0 artifacts.
    repo = tmp_path
    monkeypatch.setattr(r, "REPO", repo, raising=True)
    monkeypatch.setattr(r, "DATA", repo / "data", raising=True)
    r.main()
    out = capsys.readouterr().out
    assert "0 artifact(s) flagged" in out


def test_main_only_v3_artifacts_no_flags(tmp_path, monkeypatch, capsys):
    # a clean v3-only tree must be left entirely untouched
    repo = tmp_path
    data = repo / "data"
    snap_dir = data / "snapshots" / "2026-07-01"
    snap_dir.mkdir(parents=True)
    original = json.dumps({"snapshot_id": "deadbeef0000", "methodology_version": "m2",
                           "fetcher_version": "collect/3.0"})
    (snap_dir / "snapshot.json").write_text(original)
    monkeypatch.setattr(r, "REPO", repo, raising=True)
    monkeypatch.setattr(r, "DATA", data, raising=True)

    r.main()
    assert (snap_dir / "snapshot.json").read_text() == original   # byte-identical, untouched
    assert "0 artifact(s) flagged" in capsys.readouterr().out
