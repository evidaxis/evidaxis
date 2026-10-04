"""m4 axis 3: own-package admission, exact history, and the scoring switch."""
import json
from pathlib import Path

import pytest

from collectors import axis3_m4_identity as ident
from collectors import score_m3 as m3
from collectors import t2_deps_v2h1_collect as collect

CAPTURE = "2026-02-01T00:00:00Z"
PANEL = {
    "e_a": {("NPM", "own-a1"), ("NPM", "own-a2")},
    "e_b": {("NPM", "own-b"), ("NPM", "drop-b")},
    "e_c": {("NPM", "own-c1"), ("NPM", "own-c2"), ("NPM", "drop-c")},
    "e_d": {("NPM", "own-d1"), ("NPM", "own-d2"), ("NPM", "drop-d")},
    "e_r": {("NPM", "own-r1"), ("NPM", "own-r2"), ("NPM", "drop-r")},
    "e_none": {("NPM", "drop-only")},
}
ADMITTED = {
    ("e_a", "NPM/own-a1"), ("e_a", "NPM/own-a2"),
    ("e_b", "NPM/own-b"),
    ("e_c", "NPM/own-c1"), ("e_c", "NPM/own-c2"),
    ("e_d", "NPM/own-d1"), ("e_d", "NPM/own-d2"),
    ("e_r", "NPM/own-r1"), ("e_r", "NPM/own-r2"),
}


def _install(monkeypatch):
    monkeypatch.setattr(ident.deps, "load_panel", lambda: (PANEL, "fixture-sha"))

    def fake(entity_id, pkg):
        system, name = pkg.split("/", 1)
        return (entity_id, f"{system.upper()}/{name}") in ADMITTED

    monkeypatch.setattr(ident, "admitted", fake)


def _sys(eid, day, value, captured=CAPTURE):
    return {"entity_id": eid, "snapshot_at": day, "captured_at": captured, "coverage": "matched",
            "series": "live", "signals": {"deps_v2h1_unique_direct": {"value": value}}}


def _pkg(eid, pkg, unique, sketch):
    return {"entity_key": eid, "pkg": pkg, "unique_direct": unique, "sketch64": sketch}


def _write(root: Path, day: str, systems: list, packages: list, folder: str | None = None):
    folder_path = root / (folder or "2026-02-01")
    folder_path.mkdir(parents=True, exist_ok=True)
    (folder_path / f"deps_v2h1-{day}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in systems))
    (folder_path / f"deps_v2h1-{day}-packages.jsonl").write_text("".join(json.dumps(row) + "\n" for row in packages))


def test_admitted_truth_table(monkeypatch):
    monkeypatch.setattr(ident, "_verdicts", lambda: {
        ("e", "NPM/other"): "other_repo",
        ("e", "NPM/priv-open"): "no_link",
        ("e", "NPM/priv-ok"): "verified",
        ("e", "NPM/nolink"): "no_link",
    })
    monkeypatch.setattr(ident, "_private_flags", lambda: {("e", "NPM/priv-open"): True, ("e", "NPM/priv-ok"): True})
    assert ident.admitted("e", "NPM/other") is False
    assert ident.admitted("e", "NPM/priv-open") is False
    assert ident.admitted("e", "NPM/priv-ok") is True
    assert ident.admitted("e", "NPM/nolink") is True
    assert ident.admission_label("e", "NPM/nolink") == "unverified"
    assert ident.admission_label("e", "NPM/priv-open") == "private"


def test_real_audit_admission_matches_stored_verdicts():
    verdicts = ident._verdicts()
    private = ident._private_flags()
    other = next(key for key, verdict in verdicts.items() if verdict == "other_repo")
    no_link = next(key for key, verdict in verdicts.items() if verdict == "no_link")
    private_ok = next(key for key, verdict in verdicts.items()
                      if verdict == "verified" and private.get(key, False))
    assert ident.admitted(*other) is False
    assert ident.admitted(*no_link) is True
    assert ident.admission_label(*no_link) == "unverified"
    assert ident.admitted(*private_ok) is True


def test_panel_m4_drops_unadmitted_and_keeps_self_names():
    full, sha = collect.load_panel()
    admitted, admitted_sha = ident.load_panel_m4()
    assert admitted_sha.startswith("m4:") and admitted_sha == ident.m4_mapping_sha(sha)
    assert set(admitted) < set(full)
    for eid, pkgs in admitted.items():
        assert pkgs <= full[eid] and pkgs
    assert ident.self_names_v2h1() == {f"{system}/{name}" for pkgs in full.values() for system, name in pkgs}
    assert sum(len(pkgs) for pkgs in admitted.values()) < sum(len(pkgs) for pkgs in full.values())


def test_four_derivation_cases(tmp_path, monkeypatch):
    _install(monkeypatch)
    day = "2026-01-05"
    systems = [
        _sys("e_a", day, 9),
        _sys("e_b", day, 500),
        _sys("e_c", day, 999),
        _sys("e_d", day, 999),
        _sys("e_none", day, 12),
    ]
    packages = [
        _pkg("e_a", "NPM/own-a1", 2, [1, 2]),
        _pkg("e_a", "NPM/own-a2", 3, [2, 3, 4]),
        _pkg("e_b", "NPM/own-b", 9, [5]),
        _pkg("e_b", "NPM/drop-b", 400, [6]),
        _pkg("e_c", "NPM/own-c1", 3, [1, 2, 3]),
        _pkg("e_c", "NPM/own-c2", 2, [3, 4]),
        _pkg("e_c", "NPM/drop-c", 50, [7]),
        _pkg("e_d", "NPM/own-d1", 65, list(range(64))),
        _pkg("e_d", "NPM/own-d2", 1, [1]),
        _pkg("e_d", "NPM/drop-d", 10, [2]),
        _pkg("e_none", "NPM/drop-only", 12, [3]),
    ]
    _write(tmp_path, day, systems, packages)
    series = ident.derive_m4_series(day, tmp_path, CAPTURE)
    assert series["e_a"] == [(day, 9)]
    assert series["e_b"] == [(day, 9)]
    assert series["e_c"] == [(day, 4)]
    assert "e_d" not in series
    assert "e_none" not in series
    counts = {eid: [case for _day, case, _value in rows]
              for eid, rows in ident.partition_cases(day, tmp_path, CAPTURE).items()}
    assert counts["e_a"] == ["a"] and counts["e_b"] == ["b"] and counts["e_c"] == ["c"] and counts["e_d"] == ["d"]


def test_withheld_point_restarts_the_series(tmp_path, monkeypatch):
    _install(monkeypatch)
    days = ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"]
    _write(tmp_path, days[0], [_sys("e_r", days[0], 10)], [_pkg("e_r", "NPM/own-r1", 10, [1])])
    _write(tmp_path, days[1], [_sys("e_r", days[1], 80)], [
        _pkg("e_r", "NPM/own-r1", 65, list(range(64))),
        _pkg("e_r", "NPM/own-r2", 1, [1]),
        _pkg("e_r", "NPM/drop-r", 3, [2]),
    ], folder="2026-01-12")
    _write(tmp_path, days[2], [_sys("e_r", days[2], 4)], [
        _pkg("e_r", "NPM/own-r1", 4, [1, 2, 3, 4]),
        _pkg("e_r", "NPM/drop-r", 9, [5]),
    ], folder="2026-01-19")
    _write(tmp_path, days[3], [_sys("e_r", days[3], 6)], [_pkg("e_r", "NPM/own-r1", 6, [1])], folder="2026-01-26")
    series = ident.derive_m4_series(days[-1], tmp_path, CAPTURE)
    assert series["e_r"] == [(days[2], 4), (days[3], 6)]
    # A withheld partition that is not confirmed does not restart the run.
    kept = ident.derive_m4_series(days[-1], tmp_path, CAPTURE, confirmed={days[0], days[2], days[3]})
    assert kept["e_r"] == [(days[0], 10), (days[2], 4), (days[3], 6)]


def test_derive_uses_observation_custody(tmp_path, monkeypatch):
    _install(monkeypatch)
    day = "2026-01-05"
    _write(tmp_path, day, [_sys("e_a", day, 9)], [_pkg("e_a", "NPM/own-a1", 9, [1])])
    _write(tmp_path, day, [_sys("e_a", day, 999, captured="2026-03-01T00:00:00Z")],
           [_pkg("e_a", "NPM/own-a1", 999, [1])], folder="2026-03-01")
    series = ident.derive_m4_series(day, tmp_path, CAPTURE)
    assert series["e_a"] == [(day, 9)]


def _entity(eid="e_0"):
    return {"entity_id": eid, "name": eid, "cohort": "c", "incumbent": False,
            "axes": {m3.AXIS1: {"slope": 0.2, "cohort_z": 1.1, "recent_weekly_commits": 6},
                     m3.AXIS2: {"status": "absent", "slope": None, "cohort_z": None}}}


def _snapshot(day):
    return {"snapshot_date": day, "captured_at": f"{day}T12:00:00Z", "snapshot_id": "old",
            "period": "2026-w38", "methodology_version": "m2", "axes": {}, "entities": [_entity()]}


def test_pre_activation_snapshot_stays_m3(tmp_path):
    evidence = {"relative": "fixture.json", "sha256": "fixture", "commit": "fixture",
                "committed_at": "2026-09-19T12:00:00Z", "states": {}}
    scored = m3.score_snapshot(_snapshot("2026-09-19"), observations=tmp_path, evidence=evidence, panel={"e_0"})
    assert scored["methodology_version"] == "m3"
    assert "linkage-verified" in scored["axes"][m3.AXIS3]


def test_m4_snapshot_carries_m4(tmp_path, monkeypatch):
    evidence = {"relative": "fixture.json", "sha256": "fixture", "commit": "fixture",
                "committed_at": "2026-10-10T12:00:00Z", "states": {}}
    snap = _snapshot("2026-10-10")
    scored = m3.score_snapshot(snap, observations=tmp_path, evidence=evidence, panel={"e_0"})
    assert scored["methodology_version"] == "m4"
    description = scored["axes"][m3.AXIS3]
    assert "declared in its own tree" in description
    assert "published under that name" in description
    assert "not attributed by deps.dev to another repository" in description
    assert "unverified" in description
    assert "fixed v2h.1" in description
    data, cards = tmp_path / "data", tmp_path / "entities"
    bundle = data / "snapshots" / snap["snapshot_date"]
    bundle.mkdir(parents=True)
    cards.mkdir()
    (data / "history").mkdir()
    (data / "observations").mkdir()
    (bundle / "snapshot.json").write_bytes(m3.json_bytes(snap))
    (data / "latest.json").write_bytes(m3.json_bytes({"snapshot_date": snap["snapshot_date"], "snapshot_id": "old"}))
    for name in ("manifest.json", "provenance.json"):
        (bundle / name).write_bytes(m3.json_bytes({"methodology_version": "m2", "snapshot_id": "old"}))
    (cards / "e_0.md").write_text(f"---\nentity_id: e_0\nscore:\n  snapshot_id: old\n  captured_at: {snap['captured_at']}\n---\nBody\n")
    history = {"v": "ts_1", "entity_id": "e_0", "snapshot_id": "old", "captured_at": snap["captured_at"], "period": snap["period"]}
    (data / "history" / "e_0.jsonl").write_text(json.dumps(history) + "\n")
    monkeypatch.setattr(m3, "DATA", data)
    monkeypatch.setattr(m3, "ENTITIES", cards)
    monkeypatch.setattr(m3, "sanity_as_of", lambda *_args: evidence)
    assert m3.run() == 0
    assert m3.run(verify=True) == 0
    published = json.loads((bundle / "snapshot.json").read_text())
    assert published["methodology_version"] == "m4"
    assert json.loads((bundle / "manifest.json").read_text())["methodology_version"] == "m4"
    assert json.loads((bundle / "provenance.json").read_text())["methodology_version"] == "m4"
    assert json.loads((data / "latest.json").read_text())["methodology_version"] == "m4"
    card = (cards / "e_0.md").read_text()
    assert "methodology_version: m4" in card and "methodology m4" in card
    row = json.loads((data / "history" / "e_0.jsonl").read_text().splitlines()[-1])
    assert row["methodology_version"] == "m4"


def test_build_query_fixed_self_names_drop_excluded_from_case():
    sql = collect.build_query({"e_kept": {("NPM", "kept-pkg")}}, "2026-10-10", {"NPM/kept-pkg", "NPM/excluded-pkg"})
    case, _sep, rest = sql.partition("ELSE NULL END")
    assert "WHEN d.System = 'NPM' AND d.Name = 'kept-pkg' THEN 'e_kept'" in case
    assert "d.Name = 'excluded-pkg'" not in case
    assert "'NPM/excluded-pkg'" in rest and "'NPM/kept-pkg'" in rest
    same = {"e": {("PYPI", "alpha"), ("NPM", "beta")}}
    assert collect.build_query(same, "2026-07-13") == collect.build_query(same, "2026-07-13", {"NPM/beta", "PYPI/alpha"})


def test_forward_capture_uses_m4_mapping_and_fixed_self_names():
    full, sha = collect.load_panel()
    old_pkgs, old_sha, old_names = collect.panel_for_partition("2026-10-09")
    assert old_names is None and old_pkgs == full and old_sha == sha
    new_pkgs, new_sha, new_names = collect.panel_for_partition(ident.M4_ACTIVATION)
    admitted, admitted_sha = ident.load_panel_m4()
    assert new_pkgs == admitted and new_sha == admitted_sha and new_names == ident.self_names_v2h1()
    sql = collect.build_query(new_pkgs, ident.M4_ACTIVATION, new_names)
    case, _sep, rest = sql.partition("ELSE NULL END")
    mapped = {f"{system}/{name}" for pkgs in new_pkgs.values() for system, name in pkgs}
    missing = new_names - mapped
    assert missing
    for name in missing:
        system, pkg = name.split("/", 1)
        assert f"WHEN d.System = '{system}' AND d.Name = '{pkg}'" not in case
        assert f"'{name}'" in rest



# ---------------------------------------------------------------- review fixes 2026-10-04

def test_unaudited_panel_package_fails_loudly(monkeypatch):
    monkeypatch.setattr(ident, "_verdicts", lambda: {})
    monkeypatch.setattr(ident, "_legacy_pins", lambda: frozenset({("e_PIN", "PYPI/pinned")}))
    assert ident.admitted("e_PIN", "PYPI/pinned") is True  # legacy pin = verified by construction
    with pytest.raises(ValueError):
        ident.admitted("e_UNKNOWN", "NPM/nobody-audited-this")


def test_every_v2h1_panel_package_has_a_verdict():
    full, _sha = collect.load_panel()
    for eid, pkgs in full.items():
        for system, name in pkgs:
            ident.admitted(eid, f"{system}/{name}")  # raises when a pair is uncovered


def test_gap_in_calendar_restarts_the_run():
    points = [("2026-01-05", "a", 10), ("2026-01-12", "a", 11), ("2026-01-26", "a", 13)]
    calendar = ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"]
    assert ident._latest_run(points, None, calendar) == [("2026-01-26", 13)]
    # dates before the series starts are not gaps
    assert ident._latest_run(points[2:], None, calendar) == [("2026-01-26", 13)]
    # a date outside the confirmed set is skipped, not a gap
    assert ident._latest_run(points, {"2026-01-05", "2026-01-12", "2026-01-26"}, calendar) == [
        ("2026-01-05", 10), ("2026-01-12", 11), ("2026-01-26", 13)]
