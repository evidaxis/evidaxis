# Key registry: governance signing key (2026-10-19)

> status: PUBLISHED 2026-10-19. First publication of this key.
> Purpose: signatures on governance decisions only, under the Amendment rule of
> `CONSTITUTION.md` and section 8 of
> `governance/AMENDMENT-PROPOSAL-2026-10-19-invariant-1.md`.

## Key

| Field | Value |
|---|---|
| Algorithm | Ed25519 |
| Public key (OpenSSH) | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINbbeFTZjuGFwuAAT6x6fY4a4GgffkmBey261MPQsPJ5` |
| Fingerprint | `SHA256:f/8S8GxrgiFaILEWVe9YbRZKqu7zt2x2csrpcvcyH0Y` |
| Signer identity | `governance@evidaxis.org` |
| Namespace | `evidaxis-governance` |
| Allowed signers file | `governance/allowed_signers` |
| First published | 2026-10-19 |
| Backup restore tested | 2026-10-19: a copy restored from the steward's encrypted backup of project secrets signed a test message, and the signature verified against this public key |

## What this key does and does not authenticate

- It signs governance decisions, starting with the decision on the invariant 1 proposal
  (not before 2026-11-18). Each signature sits next to its file as `<file>.sig`, with a
  note stating the SHA-256 the steward approved and the date of approval.
- This key is new. It authenticates nothing published before this record. Earlier acts
  rest on git history and on OpenTimestamps stamps where they exist.
- It is not the dead-man heartbeat key. The heartbeat keeps its own key and procedure,
  because a heartbeat must show that the steward acts, and an automated signature with
  this key would not show that.

## Custody

The steward decides; the steward's assistant performs the mechanical steps on the
steward's own computer, and signs only after the steward approves a named file and its
SHA-256. The private key is encrypted with a passphrase kept apart from it, in a folder
with mode 0700 and a file with mode 0600, on an encrypted disk. An encrypted copy is part
of the steward's backup of project secrets. The key never enters CI, a remote machine, a
chat, a shared drive or this repository. No air gap is claimed.

## How to verify a signature

```
ssh-keygen -Y verify -f governance/allowed_signers -I governance@evidaxis.org \
  -n evidaxis-governance -s <file>.sig < <file>
```

The `governance-verify` workflow runs the same check on every push that touches a
signature.

## Timestamp

This record is stamped with OpenTimestamps: `governance/KEY-REGISTRY-2026-10-19.md.ots`.
