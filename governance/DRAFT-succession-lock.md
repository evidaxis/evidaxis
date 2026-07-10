# DRAFT — Succession lock (who may continue the canon, and how)

> status: DRAFT for keeper adjudication · created: 2026-07-10 · author: orchestrator session
> Builds on TRUST-ROOT-AND-CONTINUITY.md (canonical-fork rule, forward rotation,
> dead-man tombstone) — this draft turns the existing POLICY sketch into a lockable
> procedure. It claims no machinery that does not exist (no theater).

## What already exists (inherited, not re-decided here)

- Past integrity is key-independent (anchors + byte-reproducibility) — a successor
  never needs the old key to PROVE the past.
- Canonical-fork rule: a successor is canonical only if it keeps **CC0 +
  positive-only by construction**; a key signing a policy-violating event is
  non-canonical by published rule.
- Dead-man heartbeat + tombstone: graceful, provable dormancy.

## The gap this lock closes

The fork rule says WHAT disqualifies a successor, but not WHO/HOW one is legitimately
appointed — leaving a race-to-claim if the keeper vanishes: multiple forks, each
CC0+positive-only, each claiming the name. The name and domain are locked to the
institution (IDENTITY.md); the missing piece is an ordered succession procedure.

## Lock (proposed, forward-amendable by rotation)

1. **Succession is by signed delegation, not by inheritance of infrastructure.**
   The only legitimate succession event is a KeyRegistry rotation event signed by the
   current trust-root key (or its M-of-N successor scheme), naming the successor key.
   Domain/GitHub-org custody without a signed rotation confers NOTHING canonical.
2. **Dormancy path (keeper vanished, no rotation signed):** after the dead-man
   tombstone fires, the archive is CLOSED-canonical: the anchored record is complete
   and final; no successor may append to THE canon. Any continuation is a new lineage
   that must (a) keep CC0+positive-only, (b) cite the closed canon by DOI/URN,
   (c) use a distinct name unless the trademark/domain is legally transferred AND the
   closure is honored (the closed series stays immutable, continuation starts a new
   accession epoch with a new methodology-version namespace).
3. **Escrowed delegation (activates when custody hardens):** when the M-of-N scheme
   exists (TRUST-ROOT "later" path), a sealed successor-designation MAY be escrowed
   with the shares; it activates only through the dead-man dormancy path, and its
   activation is itself a public, anchored event.
4. **No paid succession.** The right to continue the canon is not transferable for
   consideration (mirrors the anti-roadmap: no paid inclusion — a fortiori no paid
   custody of the whole).

## Keeper action
- [ ] Adjudicate: adopt as-is / amend / reject with reason.
- [ ] If adopted: append a pointer to TRUST-ROOT-AND-CONTINUITY.md (one commit).
