"""heartbeat - keeper liveness signal for the dead-man trigger (do-once T1, cons continuity).

The keeper periodically signs a short, dated, hash-chained heartbeat with an
Ed25519 trust-root key. The signed heartbeats are public (data/integrity/heartbeat.jsonl)
and prove the keeper is still present. A laptop-independent watcher (separate private
repo, see dead-man/) reads this file; if the newest heartbeat is older than a set
window, it publishes the pre-signed TOMBSTONE and marks the archive dormant. That way
the observatory degrades gracefully and provably instead of rotting silently if the
keeper disappears. The archive itself stays readable forever (CC0 + Merkle root).

The PRIVATE key never lives in this repo (the keeper secures it; Shamir-split for recovery).
The PUBLIC key is committed (data/integrity/heartbeat-pubkey.txt) so anyone can verify.

cryptography is imported lazily so the module loads without it; signing/verifying
needs `pip install cryptography`. New code, outside frozen etl/.

Usage:
  python collectors/heartbeat.py keygen --out ~/.evidaxis/heartbeat.pem   # ONE-TIME (the keeper)
  python collectors/heartbeat.py sign   --key ~/.evidaxis/heartbeat.pem    # periodic (weekly)
  python collectors/heartbeat.py verify [--max-age-days 120]               # watcher / anyone
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import date as date_cls
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTEGRITY = REPO / "data" / "integrity"
LEDGER = INTEGRITY / "heartbeat.jsonl"
PUBKEY = INTEGRITY / "heartbeat-pubkey.txt"

_STATEMENT = "Evidaxis keeper heartbeat; archive active and maintained."
GENESIS_PREV = "0" * 64


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _lines(path: Path) -> list:
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _last_hash(path: Path) -> str:
    lines = _lines(path)
    return hashlib.sha256(lines[-1].encode("utf-8")).hexdigest() if lines else GENESIS_PREV


def _require_crypto():
    """Fail fast with a helpful message if cryptography is not installed."""
    if importlib.util.find_spec("cryptography") is None:
        print("heartbeat: needs the `cryptography` package -> pip install cryptography", file=sys.stderr)
        raise SystemExit(2)


def message_for(dt: str, prev_hash: str) -> str:
    """The exact bytes-string that gets signed. Binds date + chain tip + statement."""
    return _canonical({"date": dt, "prev_hash": prev_hash, "statement": _STATEMENT})


def keygen(out_path: Path) -> str:
    _require_crypto()
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv = Ed25519PrivateKey.generate()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    fp = "ed25519:" + pub_raw.hex()
    INTEGRITY.mkdir(parents=True, exist_ok=True)
    PUBKEY.write_text(fp + "\n", encoding="utf-8")
    return fp


def _load_priv(key_path: Path):
    _require_crypto()
    from cryptography.hazmat.primitives import serialization
    return serialization.load_pem_private_key(key_path.read_bytes(), password=None)


def _pub_fp(priv) -> str:
    from cryptography.hazmat.primitives import serialization
    raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    return "ed25519:" + raw.hex()


def sign(key_path: Path, dt: str | None = None) -> dict:
    priv = _load_priv(key_path)
    dt = dt or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prev = _last_hash(LEDGER)
    msg = message_for(dt, prev)
    sig = priv.sign(msg.encode("utf-8")).hex()
    record = {
        "v": "heartbeat_1", "date": dt, "message": msg,
        "pubkey": _pub_fp(priv), "signature": sig, "prev_hash": prev,
    }
    INTEGRITY.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(_canonical(record) + "\n")
    return record


def verify(max_age_days: int | None = None) -> tuple:
    """Verify every signature + the chain, and check freshness. Returns (ok, msg)."""
    _require_crypto()
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if not PUBKEY.exists():
        return False, "no heartbeat-pubkey.txt (run keygen first)"
    fp = PUBKEY.read_text().strip()
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(fp.split(":", 1)[1]))

    lines = _lines(LEDGER)
    if not lines:
        return False, "no heartbeats recorded"
    prev = GENESIS_PREV
    latest = None
    for i, line in enumerate(lines):
        rec = json.loads(line)
        # The signature only covers rec["message"]; bind it to the fields that drive
        # the dead-man decision, else a ledger holder could forge the top-level date
        # (freshness) or prev_hash (chain) while keeping an old valid signature.
        if rec.get("message") != message_for(rec.get("date", ""), rec.get("prev_hash", "")):
            return False, f"line {i}: signed message does not match its date/prev_hash (forged)"
        if rec.get("prev_hash") != prev:
            return False, f"line {i}: chain broken"
        if rec.get("pubkey") != fp:
            return False, f"line {i}: signed by an unexpected key"
        try:
            pub.verify(bytes.fromhex(rec["signature"]), rec["message"].encode("utf-8"))
        except InvalidSignature:
            return False, f"line {i}: signature does not verify"
        latest = rec["date"]
        prev = hashlib.sha256(line.encode("utf-8")).hexdigest()

    if max_age_days is not None:
        age = (date_cls.today() - date_cls.fromisoformat(latest)).days
        if age > max_age_days:
            return False, f"STALE: last heartbeat {latest} is {age}d old (> {max_age_days}d) -> dead-man condition"
        return True, f"alive: last heartbeat {latest} ({age}d old, within {max_age_days}d)"
    return True, f"chain + signatures OK; last heartbeat {latest}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Evidaxis keeper heartbeat (dead-man trigger).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("keygen"); g.add_argument("--out", required=True)
    s = sub.add_parser("sign"); s.add_argument("--key", required=True); s.add_argument("--date", default=None)
    v = sub.add_parser("verify"); v.add_argument("--max-age-days", type=int, default=None)
    args = ap.parse_args()

    if args.cmd == "keygen":
        fp = keygen(Path(args.out).expanduser())
        print(f"keypair generated. private -> {args.out} (SECURE THIS). public -> {PUBKEY.relative_to(REPO)} ({fp})")
        return 0
    if args.cmd == "sign":
        rec = sign(Path(args.key).expanduser(), args.date)
        print(f"heartbeat signed for {rec['date']} ({rec['pubkey'][:20]}...)")
        return 0
    ok, msg = verify(args.max_age_days)
    print(f"heartbeat verify: {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
