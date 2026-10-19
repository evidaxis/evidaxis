#!/usr/bin/env python3
"""Sign a governance file with the steward's encrypted Ed25519 key.

cryptography is imported lazily so the module loads without it. Signing needs
`pip install cryptography`. Same exception as collectors/heartbeat.py: this
script is outside frozen etl/, and the dependency is already pinned in
requirements-dev.txt.

The passphrase is read from a file. It is never accepted as an argument,
because a hook records the command line.

    python3 scripts/governance_sign.py keygen [--key PATH] [--passphrase-file PATH]
    python3 scripts/governance_sign.py restore-test --backup COPY [--passphrase-file PATH]
    python3 scripts/governance_sign.py sign --file F --expect-sha256 H [--key PATH] [--passphrase-file PATH]

keygen writes a PKCS8 PEM encrypted with BestAvailableEncryption. The default
directory is ~/.evidaxis/ (mode 0700). The key and the passphrase file are
mode 0600. It prints the OpenSSH public key and one allowed_signers line.

restore-test decrypts a backup copy into a temporary directory, signs a test
message, and checks it with ssh-keygen -Y verify.

sign recomputes SHA-256 of F and refuses when it differs from --expect-sha256.
On a match it writes F.sig (OpenSSH SSHSIG, namespace evidaxis-governance,
hash sha512) and F.approval.txt (the approved SHA-256 and the UTC date).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import secrets
import shutil
import struct
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

NAMESPACE = "evidaxis-governance"
IDENTITY = "governance@evidaxis.org"
HASH_NAME = "sha512"
_MAGIC = b"SSHSIG"
_HOME_DIR = Path.home() / ".evidaxis"
_DEFAULT_KEY = _HOME_DIR / "governance_ed25519.pem"
_DEFAULT_PASS = _HOME_DIR / "governance_ed25519.passphrase"


class SignError(Exception):
    """A safe message. It never includes the passphrase or the private key."""


def _require_crypto():
    import importlib.util

    if importlib.util.find_spec("cryptography") is None:
        raise SignError("needs the cryptography package")


def _ssh_string(data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + data


def _public_blob(raw_key: bytes) -> bytes:
    return _ssh_string(b"ssh-ed25519") + _ssh_string(raw_key)


def openssh_public_line(raw_key: bytes) -> str:
    return "ssh-ed25519 " + base64.b64encode(_public_blob(raw_key)).decode("ascii")


def allowed_signers_line(raw_key: bytes) -> str:
    return f'{IDENTITY} namespaces="{NAMESPACE}" {openssh_public_line(raw_key)}'


def sshsig(private_key, message: bytes) -> str:
    """Armored SSHSIG signature over message. OpenSSH PROTOCOL.sshsig."""
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    digest = hashlib.sha512(message).digest()
    signed = (
        _MAGIC
        + _ssh_string(NAMESPACE.encode("ascii"))
        + _ssh_string(b"")
        + _ssh_string(HASH_NAME.encode("ascii"))
        + _ssh_string(digest)
    )
    raw_sig = private_key.sign(signed)
    sig_blob = _ssh_string(b"ssh-ed25519") + _ssh_string(raw_sig)
    outer = (
        _MAGIC
        + struct.pack(">I", 1)
        + _ssh_string(_public_blob(raw))
        + _ssh_string(NAMESPACE.encode("ascii"))
        + _ssh_string(b"")
        + _ssh_string(HASH_NAME.encode("ascii"))
        + _ssh_string(sig_blob)
    )
    encoded = base64.b64encode(outer).decode("ascii")
    lines = [encoded[i:i + 70] for i in range(0, len(encoded), 70)]
    return "-----BEGIN SSH SIGNATURE-----\n" + "\n".join(lines) + "\n-----END SSH SIGNATURE-----\n"


def _tighten(directory: Path) -> None:
    resolved = directory.resolve()
    if resolved == Path.home().resolve() or resolved == Path(resolved.anchor):
        raise SignError("refusing to change the home directory mode")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o700)
    except OSError as exc:
        raise SignError("output unavailable") from exc


def _write_private(path: Path, data: bytes) -> None:
    _tighten(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    try:
        fd = os.open(path, flags, 0o600)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
        finally:
            os.close(fd)
        os.chmod(path, 0o600)
    except OSError as exc:
        raise SignError("output unavailable") from exc


def _read_passphrase(path: Path) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SignError("passphrase file unreadable") from exc
    if data.endswith(b"\n"):
        data = data[:-1]
    if data.endswith(b"\r"):
        data = data[:-1]
    if not data:
        raise SignError("passphrase file unreadable")
    return data


def _load_private(path: Path, passphrase: bytes):
    _require_crypto()
    from cryptography.hazmat.primitives import serialization

    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=passphrase)
    except (OSError, ValueError) as exc:
        raise SignError("key unreadable") from exc
    return key


def _raw_public(private_key) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _generate():
    _require_crypto()
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    return private_key


def _pem(private_key, passphrase: bytes) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )


def keygen(key_path: Path, passphrase_path: Path) -> int:
    if key_path.exists() or passphrase_path.exists():
        raise SignError("key already exists")
    passphrase = secrets.token_urlsafe(32).encode("ascii")
    private_key = _generate()
    _write_private(passphrase_path, passphrase + b"\n")
    try:
        _write_private(key_path, _pem(private_key, passphrase))
    except SignError:
        passphrase_path.unlink(missing_ok=True)
        raise
    raw = _raw_public(private_key)
    print(openssh_public_line(raw))
    print(allowed_signers_line(raw))
    return 0


def _verify_with_openssh(message: bytes, signature: Path, signers: Path) -> None:
    if shutil.which("ssh-keygen") is None:
        raise SignError("ssh-keygen missing")
    try:
        proc = subprocess.run(
            [
                "ssh-keygen", "-Y", "verify",
                "-f", str(signers),
                "-I", IDENTITY,
                "-n", NAMESPACE,
                "-s", str(signature),
            ],
            input=message,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise SignError("ssh-keygen missing") from exc
    if proc.returncode != 0:
        raise SignError("signature rejected")


def restore_test(backup: Path, passphrase_path: Path) -> int:
    passphrase = _read_passphrase(passphrase_path)
    try:
        pem = backup.read_bytes()
    except OSError as exc:
        raise SignError("key unreadable") from exc
    message = b"evidaxis governance restore test\n"
    # The backup stays where it is. The decrypted copy lives only in this temp dir.
    with tempfile.TemporaryDirectory(prefix="evx-governance-") as raw_dir:
        directory = Path(raw_dir)
        os.chmod(directory, 0o700)
        key_path = directory / "key.pem"
        _write_private(key_path, pem)
        private_key = _load_private(key_path, passphrase)
        signature = directory / "message.sig"
        signature.write_text(sshsig(private_key, message), encoding="ascii")
        os.chmod(signature, 0o600)
        signers = directory / "allowed_signers"
        signers.write_text(allowed_signers_line(_raw_public(private_key)) + "\n", encoding="ascii")
        _verify_with_openssh(message, signature, signers)
    print("restore-test: ok")
    return 0


def _expect_digest(file_bytes: bytes, expected: str) -> str:
    actual = hashlib.sha256(file_bytes).hexdigest()
    token = expected.strip().lower()
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token) or token != actual:
        raise SignError("sha256 mismatch")
    return actual


def sign(document: Path, expected: str, key_path: Path, passphrase_path: Path) -> int:
    try:
        payload = document.read_bytes()
    except OSError as exc:
        raise SignError("document unreadable") from exc
    digest = _expect_digest(payload, expected)
    private_key = _load_private(key_path, _read_passphrase(passphrase_path))
    signature_path = Path(str(document) + ".sig")
    approval_path = Path(str(document) + ".approval.txt")
    signature_path.write_text(sshsig(private_key, payload), encoding="ascii")
    approved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    approval_path.write_text(f"sha256: {digest}\nutc_date: {approved_at}\n", encoding="ascii")
    print(f"governance signature: {signature_path.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="governance_sign.py")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("keygen")
    generate.add_argument("--key", type=Path, default=_DEFAULT_KEY)
    generate.add_argument("--passphrase-file", type=Path, default=_DEFAULT_PASS)

    restore = commands.add_parser("restore-test")
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--passphrase-file", type=Path, default=_DEFAULT_PASS)

    signer = commands.add_parser("sign")
    signer.add_argument("--file", type=Path, required=True)
    signer.add_argument("--expect-sha256", required=True)
    signer.add_argument("--key", type=Path, default=_DEFAULT_KEY)
    signer.add_argument("--passphrase-file", type=Path, default=_DEFAULT_PASS)

    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            return keygen(args.key, args.passphrase_file)
        if args.command == "restore-test":
            return restore_test(args.backup, args.passphrase_file)
        return sign(args.file, args.expect_sha256, args.key, args.passphrase_file)
    except SignError as exc:
        print(f"governance signature: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
