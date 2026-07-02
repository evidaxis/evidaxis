# Dead-man trigger — graceful, provable dormancy if the keeper disappears

> created: 2026-07-02 · status: mechanism live (heartbeat), activation pending Keeper actions
> Do-once T1 (do-once-master). Continuity invariant: the archive outlives the keeper.

## The problem

Evidaxis is a 10 to 15 year, single-keeper observatory. If the keeper vanishes
(illness, loss of access, worse), the archive must NOT rot silently or, worse,
keep implying it is actively maintained when it is not. It should degrade
**gracefully and provably**: mark itself dormant, publish a signed tombstone, and
stay readable forever (CC0 + the Merkle root already guarantee readability).

## The mechanism (two halves)

1. **Heartbeat (public, in THIS repo).** The keeper periodically signs a short,
   dated, hash-chained liveness record with an Ed25519 trust-root key:
   `collectors/heartbeat.py sign --key <private.pem>` appends to
   `data/integrity/heartbeat.jsonl`. The public key is at
   `data/integrity/heartbeat-pubkey.txt`. Anyone can verify with
   `heartbeat.py verify [--max-age-days N]`.

2. **Watcher (SEPARATE private repo, laptop-independent).** A GitHub Action in a
   private `evidaxis-watcher` repo runs daily, fetches the public heartbeat +
   pubkey, and runs `heartbeat.py verify --max-age-days N`. If the newest heartbeat
   is older than the window (default 120 days), the watcher publishes the
   pre-signed `TOMBSTONE.md` into the public repo and flips the archive to
   `dormant`. The watcher lives OUTSIDE the keeper's machine so it fires even if
   the keeper is fully gone. Template: `dead-man/watcher.workflow.yml`.

Why two repos: the trigger must not depend on the very thing that failed. A watcher
inside the main repo, driven by the keeper's own automation, is not a dead-man
switch. A separate repo with its own schedule and its own publish credential is.

## Keeper actions (one-time; code + docs are ready, these need a human with the key)

1. **Generate the trust-root key** on a secure machine:
   `python collectors/heartbeat.py keygen --out ~/.evidaxis/heartbeat.pem`
   Commit the printed `data/integrity/heartbeat-pubkey.txt` (public) to this repo.
   NEVER commit the `.pem` (private).
2. **Secure + Shamir-split the private key.** Split `heartbeat.pem` (and a short
   "how to continue Evidaxis" instruction sheet + the resolver/backup notes) into a
   3-of-5 Shamir secret share across 2 to 5 trusted holders, plus a sealed escrow
   copy. This is both the recovery path and the succession path.
3. **Sign the first heartbeat** and set a recurring reminder (weekly is ample; the
   watcher window is months). `heartbeat.py sign --key ~/.evidaxis/heartbeat.pem`.
   Automate it later from a trusted machine if desired.
4. **Create the `evidaxis-watcher` private repo**, drop in `watcher.workflow.yml`
   (adjust the placeholders), and give it a fine-scoped token/deploy-key that can
   push ONLY `TOMBSTONE.md` + `data/latest.json` to the public repo.
5. **Pre-sign the tombstone** (optional, stronger): sign `TOMBSTONE.md` with the
   trust-root key now and store the signature with the watcher, so the published
   tombstone is provably the keeper's, not the watcher operator's.

Until steps 1 to 4 are done the heartbeat mechanism is inert (no key, no ledger);
nothing about the live site changes. Activation is entirely in the keeper's hands.
