"""Dead-man heartbeat: keygen -> sign -> verify round-trip, staleness, tamper.

Skips cleanly if `cryptography` is absent so the rest of the suite still runs.
Paths are redirected to a tmp dir so the real repo ledger is never touched."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
import heartbeat


@pytest.fixture
def hb(tmp_path, monkeypatch):
    monkeypatch.setattr(heartbeat, "INTEGRITY", tmp_path)
    monkeypatch.setattr(heartbeat, "LEDGER", tmp_path / "heartbeat.jsonl")
    monkeypatch.setattr(heartbeat, "PUBKEY", tmp_path / "heartbeat-pubkey.txt")
    return tmp_path


def test_keygen_sign_verify_roundtrip(hb):
    key = hb / "priv.pem"
    heartbeat.keygen(key)
    heartbeat.sign(key, dt="2026-07-01")
    heartbeat.sign(key, dt="2026-07-02")
    ok, msg = heartbeat.verify()
    assert ok, msg
    assert "2026-07-02" in msg


def test_stale_heartbeat_trips_deadman(hb):
    key = hb / "priv.pem"
    heartbeat.keygen(key)
    heartbeat.sign(key, dt="2020-01-01")  # ancient
    ok, msg = heartbeat.verify(max_age_days=120)
    assert not ok and "STALE" in msg


def test_fresh_heartbeat_is_alive(hb):
    from datetime import date
    key = hb / "priv.pem"
    heartbeat.keygen(key)
    heartbeat.sign(key, dt=date.today().isoformat())
    ok, msg = heartbeat.verify(max_age_days=120)
    assert ok and "alive" in msg


def test_tampered_signature_fails(hb):
    import json
    key = hb / "priv.pem"
    heartbeat.keygen(key)
    heartbeat.sign(key, dt="2026-07-01")
    ledger = hb / "heartbeat.jsonl"
    rec = json.loads(ledger.read_text().strip())
    sig = list(rec["signature"])
    sig[0] = "0" if sig[0] != "0" else "1"  # flip one hex char -> signature no longer valid
    rec["signature"] = "".join(sig)
    ledger.write_text(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
    ok, _ = heartbeat.verify()
    assert not ok


def test_verify_needs_a_key(hb):
    ok, msg = heartbeat.verify()
    assert not ok and "pubkey" in msg


def test_forged_top_level_date_is_caught(hb):
    # adversary edits ONLY the unsigned top-level date to look fresh, keeping the old
    # valid signature. The message<->date binding must catch it (else STALE->alive).
    import json
    key = hb / "priv.pem"
    heartbeat.keygen(key)
    heartbeat.sign(key, dt="2020-01-01")
    ledger = hb / "heartbeat.jsonl"
    rec = json.loads(ledger.read_text().strip())
    rec["date"] = "2099-01-01"  # message still encodes 2020-01-01
    ledger.write_text(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
    ok, msg = heartbeat.verify(max_age_days=120)
    assert not ok and "forged" in msg


def test_history_truncation_is_caught(hb):
    # deleting the genesis record and relinking the survivor's prev_hash to GENESIS
    # must fail: the survivor's SIGNED message binds its original prev_hash.
    import json
    key = hb / "priv.pem"
    heartbeat.keygen(key)
    heartbeat.sign(key, dt="2026-07-01")
    heartbeat.sign(key, dt="2026-07-02")
    ledger = hb / "heartbeat.jsonl"
    lines = ledger.read_text().splitlines()
    survivor = json.loads(lines[1])
    survivor["prev_hash"] = heartbeat.GENESIS_PREV  # pretend it was the genesis
    ledger.write_text(json.dumps(survivor, sort_keys=True, separators=(",", ":")) + "\n")
    ok, _ = heartbeat.verify()
    assert not ok
