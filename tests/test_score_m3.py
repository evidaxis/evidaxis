"""Temporal, gate and publication contracts for the forward m3 post-step."""
import copy
import json
from datetime import date, timedelta

import pytest

from collectors import score_m3 as m3
from collectors.axis3_inputs import sanity_as_of

PARTITIONS = [(date(2026, 6, 1) + timedelta(weeks=i)).isoformat() for i in range(16)]
CAPTURE = "2026-09-19T12:00:00Z"
EVIDENCE = {"relative": "fixture.json", "sha256": "fixture", "commit": "fixture",
            "committed_at": CAPTURE, "states": dict.fromkeys(PARTITIONS, "CLEAN")}


def entity(eid="e_A", cohort="c"):
    return {"entity_id": eid, "name": eid, "cohort": cohort, "incumbent": False,
            "axes": {m3.AXIS1: {"slope": 0.2, "cohort_z": 1.1, "recent_weekly_commits": 6},
                     m3.AXIS2: {"status": "absent", "slope": None, "cohort_z": None}}}


def snapshot():
    return {"snapshot_date": "2026-09-19", "captured_at": CAPTURE, "snapshot_id": "old",
            "period": "2026-w38", "methodology_version": "m2", "axes": {},
            "entities": [entity(f"e_{i}") for i in range(6)]}


def observations(root, snap, values=None):
    for i, partition in enumerate(PARTITIONS):
        folder = root / ("backfill/axis3-deps-v2h1" if i < 7 else "2026-09-19")
        folder.mkdir(parents=True, exist_ok=True)
        rows = [{"entity_id": e["entity_id"], "snapshot_at": partition, "captured_at": CAPTURE,
                 "coverage": "matched", "series": "baseline-candidate" if i < 7 else "live",
                 "signals": {"deps_v2h1_unique_direct": {"value": values[i] if values else 100 + i * (j + 1)}}}
                for j, e in enumerate(snap["entities"])]
        (folder / f"deps_v2h1-{partition}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def score(snap, obs, evidence=EVIDENCE, panel=None):
    return m3.score_snapshot(snap, observations=obs, evidence=evidence,
                             panel=set(panel) if panel is not None else {e["entity_id"] for e in snap["entities"]})


def test_lookahead_partition_date(tmp_path):
    snap = snapshot()
    observations(tmp_path, snap)
    early = {**snap, "snapshot_date": PARTITIONS[-2]}
    result = score(early, tmp_path)
    assert result["axis3_cutoff"] == PARTITIONS[-2]
    assert all(e["axes"][m3.AXIS3]["points"] == 15 for e in result["entities"])


@pytest.mark.parametrize("timestamp", ["2026-09-19T12:00:00.001Z", "2026-09-19T13:01:00+01:00", None, "invalid"])
def test_lookahead_capture_time(tmp_path, timestamp):
    snap = snapshot()
    observations(tmp_path, snap)
    path = tmp_path / "2026-09-19" / f"deps_v2h1-{PARTITIONS[-1]}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        row["captured_at"] = timestamp
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    result = score(snap, tmp_path)
    assert result["axis3_cutoff"] == PARTITIONS[-2]
    assert result["entities"][0]["axes"][m3.AXIS3]["points"] == 15


def test_late_duplicate_does_not_replace_available_capture(tmp_path):
    snap = snapshot()
    observations(tmp_path, snap)
    source = tmp_path / "2026-09-19" / f"deps_v2h1-{PARTITIONS[-1]}.jsonl"
    late = tmp_path / "2026-09-20" / source.name
    late.parent.mkdir()
    late.write_text(source.read_text().replace(CAPTURE, "2026-09-20T12:00:00Z").replace('"value": 115', '"value": 999999'))
    result = score(snap, tmp_path)
    assert result["entities"][0]["axes"][m3.AXIS3]["latest"] == 115


def test_provisional_and_unknown_never_scored(tmp_path):
    snap = snapshot()
    observations(tmp_path, snap)
    states = {**EVIDENCE["states"], PARTITIONS[-1]: "PROVISIONAL"}
    del states[PARTITIONS[-2]]
    result = score(snap, tmp_path, {**EVIDENCE, "states": states})
    axis = result["entities"][0]["axes"][m3.AXIS3]
    assert result["axis3_cutoff"] == PARTITIONS[-3]
    assert axis["points"] == 14
    assert axis["points_reconstructable"] == 7


def test_held_cohort(tmp_path):
    snap = snapshot()
    # Endpoint returns to its initial value while OLS is positive.
    observations(tmp_path, snap, [100, *range(10, 24), 100])
    result = score(snap, tmp_path)
    for e in result["entities"]:
        axis = e["axes"][m3.AXIS3]
        assert axis["status"] == "held"
        assert axis["cohort_z"] is None and not axis["rising_vote"]
        assert m3.AXIS3 not in e["axes_present"]


def test_canary_needs_three_voting_entities(tmp_path):
    snap = snapshot()
    snap["entities"] = snap["entities"][:2]
    observations(tmp_path, snap, [100, *range(10, 24), 100])
    result = score(snap, tmp_path)
    assert all(e["axes"][m3.AXIS3]["status"] == "scored" for e in result["entities"])


def test_unstable_veto(tmp_path):
    snap = snapshot()
    observations(tmp_path, snap, [100] * 15 + [140])
    result = score(snap, tmp_path)
    for e in result["entities"]:
        axis = e["axes"][m3.AXIS3]
        assert axis["status"] == "scored" and axis["unstable"]
        assert not axis["rising_vote"] and m3.AXIS3 not in e["convergent_axes"]


def test_rounded_zero_slope_cannot_publish_a_rising_vote():
    snap = snapshot()
    changes = [-1, -2, -3, -4, -5, 30]
    series = {e["entity_id"]: [(partition, 100_000_000 + change * (i - 15))
                               for i, partition in enumerate(PARTITIONS)]
              for e, change in zip(snap["entities"], changes, strict=True)}
    records, _cutoff = m3.axis3_records(snap, series, EVIDENCE["states"], set(series), {})
    axis = records["e_5"]
    assert axis["status"] == "scored" and axis["slope"] == 0 and axis["cohort_z"] == 3
    assert not axis["rising_vote"]


@pytest.mark.parametrize("age,expected", [(28, "scored"), (29, "stale")])
def test_staleness_boundary(tmp_path, age, expected):
    snap = snapshot()
    snap["snapshot_date"] = (date.fromisoformat(PARTITIONS[-1]) + timedelta(days=age)).isoformat()
    observations(tmp_path, snap)
    axis = score(snap, tmp_path)["entities"][0]["axes"][m3.AXIS3]
    assert axis["status"] == expected
    if expected == "stale":
        assert axis["slope"] is None and axis["cohort_z"] is None and not axis["rising_vote"]
        assert axis["latest"] == 115 and axis["points"] == 16


def test_no_clean_partition_is_stale_not_below_floor(tmp_path):
    snap = snapshot()
    observations(tmp_path, snap)
    states = {p: "PROVISIONAL" for p in PARTITIONS}
    result = score(snap, tmp_path, {**EVIDENCE, "states": states})
    axis = result["entities"][0]["axes"][m3.AXIS3]
    assert result["axis3_cutoff"] is None
    assert axis["status"] == "stale" and not axis["rising_vote"]


def test_card_body_without_momentum_reads_na(tmp_path):
    snap = snapshot()
    observations(tmp_path, snap)
    scored = score(snap, tmp_path)
    entity = {**scored["entities"][0], "momentum": None}
    text = f"---\nentity_id: {entity['entity_id']}\nscore:\n  snapshot_id: old\n---\nBody\n"
    body = m3.card_text(text, entity, scored).split("\n---\n", 1)[1]
    assert "Momentum n/a;" in body and "None" not in body


def test_out_of_panel_and_below_floor(tmp_path):
    snap = snapshot()
    observations(tmp_path, snap, [4] * 16)
    result = score(snap, tmp_path, panel=["e_0"])
    first, second = (e["axes"][m3.AXIS3] for e in result["entities"][:2])
    assert first["status"] == "below_floor" and first["latest"] == 4
    assert second["status"] == "out_of_panel" and second["points"] is None
    assert all(m3.AXIS3 not in e["axes_present"] for e in result["entities"])


def test_m2_reproduction_invariant():
    original = json.loads((m3.DATA / "snapshots/2026-09-12/snapshot.json").read_text())
    # The test isolates aggregate semantics from axis 3 by excluding every id.
    result = score(original, m3.DATA / "observations", panel=[])
    for before, after in zip(original["entities"], result["entities"], strict=True):
        assert {k: after[k] for k in m3.ENTITY_FIELDS} == {k: before[k] for k in m3.ENTITY_FIELDS}, before["entity_id"]
        assert after["axes"][m3.AXIS1] == before["axes"][m3.AXIS1]
        assert after["axes"][m3.AXIS2] == before["axes"][m3.AXIS2]


def test_confirmation_cannot_look_ahead():
    check = sanity_as_of("2026-09-12T11:03:57+00:00")
    assert check["states"]["2026-08-31"] == "PROVISIONAL"
    assert check["relative"].endswith("sanity-check-9ec385dfa6be.json")


def setup_bundle(tmp_path, monkeypatch, before_activation=False):
    snap = snapshot()
    if before_activation:
        snap["snapshot_date"] = "2026-09-12"
    data, cards = tmp_path / "data", tmp_path / "entities"
    bundle = data / "snapshots" / snap["snapshot_date"]
    bundle.mkdir(parents=True)
    cards.mkdir()
    (data / "history").mkdir()
    (bundle / "snapshot.json").write_bytes(m3.json_bytes(snap))
    (data / "latest.json").write_bytes(m3.json_bytes({"snapshot_date": snap["snapshot_date"], "snapshot_id": "stale-pointer"}))
    for name in ("manifest.json", "provenance.json"):
        (bundle / name).write_bytes(m3.json_bytes({"methodology_version": "m2", "snapshot_id": "old"}))
    for e in snap["entities"]:
        eid = e["entity_id"]
        (cards / f"{eid}.md").write_text(f"---\nentity_id: {eid}\nscore:\n  snapshot_id: old\n  captured_at: {CAPTURE}\n---\nBody\n")
        history = {"v": "ts_1", "entity_id": eid, "snapshot_id": "old", "captured_at": CAPTURE, "period": snap["period"]}
        prior = ' {"v":"ts_1", "snapshot_id":"old", "period":"2026-w37", "captured_at":"2026-09-12T10:00:00Z"} \n'
        (data / "history" / f"{eid}.jsonl").write_text(prior + json.dumps(history) + "\n")
    observations(data / "observations", snap)
    monkeypatch.setattr(m3, "DATA", data)
    monkeypatch.setattr(m3, "ENTITIES", cards)
    monkeypatch.setattr(m3, "sanity_as_of", lambda *_args: EVIDENCE)
    monkeypatch.setattr(m3, "load_panel", lambda: ({e["entity_id"]: [] for e in snap["entities"]}, "fixture"))
    return data, cards, bundle


def test_idempotence_verify_and_capture_sync(tmp_path, monkeypatch):
    data, cards, bundle = setup_bundle(tmp_path, monkeypatch)
    history = data / "history/e_0.jsonl"
    prior = history.read_bytes().splitlines(keepends=True)[0]
    assert m3.run() == 0
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert m3.run() == 0 and m3.run(verify=True) == 0
    assert all(p.read_bytes() == blob for p, blob in before.items())
    assert history.read_bytes().splitlines(keepends=True)[0] == prior
    snap = json.loads((bundle / "snapshot.json").read_text())
    row = json.loads(history.read_text().splitlines()[-1])
    assert row["methodology_version"] == "m3" and row["axis3_z"] == snap["entities"][0]["axes"][m3.AXIS3]["cohort_z"]
    assert json.loads((data / "latest.json").read_text())["snapshot_id"] == "old"
    card = cards / "e_0.md"
    card.write_text(card.read_text().replace("methodology_version: m3", "methodology_version: m2"))
    assert m3.run(verify=True) == 1


@pytest.mark.parametrize("relative", ["snapshots/2026-09-19/snapshot.json", "snapshots/2026-09-19/manifest.json", "snapshots/2026-09-19/provenance.json", "history/e_0.jsonl", "latest.json"])
def test_verify_detects_drift_in_every_mirror(tmp_path, monkeypatch, relative):
    data, _cards, _bundle = setup_bundle(tmp_path, monkeypatch)
    assert m3.run() == 0
    path = data / relative
    path.write_bytes(path.read_bytes().replace(b'"methodology_version": "m3"', b'"methodology_version": "m2"'))
    assert m3.run(verify=True) == 1


def test_refusal_and_isolated_dry_run(tmp_path, monkeypatch):
    data, cards, _bundle = setup_bundle(tmp_path, monkeypatch, before_activation=True)
    before = {p: p.read_bytes() for root in (data, cards) for p in root.rglob("*") if p.is_file()}
    # Before activation a weekly run is a no-op (exit 0), so a manual dispatch cannot
    # fail the m2 publication; the file comparison below proves nothing was written.
    assert m3.run() == 0
    assert m3.run(verify=True) == 0
    preview = tmp_path / "preview"
    assert m3.run(dry_run=True, out_dir=preview) == 0
    assert m3.run(dry_run=True, out_dir=preview) == 0
    assert m3.run(dry_run=True, out_dir=preview, verify=True) == 0
    assert all(p.read_bytes() == blob for p, blob in before.items())


def test_historical_preview_does_not_read_later_cards_or_publish_future_snapshots(tmp_path, monkeypatch):
    data, cards, bundle = setup_bundle(tmp_path, monkeypatch)
    future = data / "snapshots/2026-09-26"
    future.mkdir()
    doc = json.loads((bundle / "snapshot.json").read_text())
    (future / "snapshot.json").write_bytes(m3.json_bytes({**doc, "snapshot_date": "2026-09-26"}))
    (data / "latest.json").write_bytes(m3.json_bytes({"snapshot_date": "2026-09-26", "snapshot_id": "newer"}))
    card = cards / "e_0.md"
    card.write_text(card.read_text().replace("snapshot_id: old", "snapshot_id: newer"))
    preview = tmp_path / "preview"
    assert m3.run("2026-09-19", dry_run=True, out_dir=preview) == 0
    assert not (preview / "snapshots/2026-09-26").exists()
    assert future.exists() and "snapshot_id: newer" in card.read_text()
    assert m3.run(dry_run=True, out_dir=preview, verify=True) == 0


def test_gate_any_two_and_reference_floor():
    entities = [entity(str(i)) for i in range(5)]
    for e in entities:
        e["axes"][m3.AXIS3] = {"status": "scored", "cohort_z": 1.5, "rising_vote": True}
    entities[-1]["incumbent"] = True
    m3.aggregate_entities(entities)
    assert [e["rising"] for e in entities] == [True] * 4 + [False]
    assert entities[0]["convergent_axes"] == [m3.AXIS1, m3.AXIS3]
    small = copy.deepcopy(entities[:4])
    m3.aggregate_entities(small)
    assert not any(e["rising"] for e in small)


def test_correlations_center_within_cohorts_and_handle_undefined():
    entities = []
    for offset in (0, 100):
        for i in range(5):
            e = entity(f"{offset}-{i}", str(offset))
            e["axes"][m3.AXIS1]["cohort_z"] = i + offset
            e["axes"][m3.AXIS2]["cohort_z"] = 1
            e["axes"][m3.AXIS3] = {"status": "scored", "cohort_z": i - offset}
            entities.append(e)
    result = m3.axis_correlations(entities)
    assert result[f"{m3.AXIS3}__{m3.AXIS1}"]["r"] == 1
    assert result[f"{m3.AXIS3}__{m3.AXIS1}"]["pairs"] == 10
    assert result[f"{m3.AXIS3}__{m3.AXIS2}"]["r"] is None
