# Evidaxis Constitution

> The invariants of this project, stated once, in plain language, so they can be
> cited, checked, and held against us. This document is the constitutional
> contract of the archive. Its hash is anchored with the next signed manifest
> (Ed25519 block-zero key, OpenTimestamps). It supersedes nothing frozen in the
> genesis deposit; it makes explicit the rules that genesis already implied.
>
> created: 2026-07-01 · status: v1 · provenance: 7-model council (cons-05 do-once), synthesis locked

## What Evidaxis is

Evidaxis is a public observatory of **rising AI systems** (repositories, models,
organizations, products, labs, never people). It is the canonical first-source of
**non-reconstructable point-in-time signals**: measurements that the world
overwrites and cannot be recovered later (watcher counts, open-issue counts,
dependent counts, on a date). Its value is being the archive that captured them
first and never rewrote them.

Evidaxis is **not an oracle**. It publishes no public prediction, no ranking of
winners, no "invest in X". It records what was measurable, when, and lets the
reader sort for themselves. Any forward hypothesis is private (see Invariant 5).

## Invariants (load-bearing, permanent)

1. **Systems, not people.** No natural-person name, handle, email, avatar, or
   contributor identity is stored or published. Enforced mechanically: a snapshot
   containing a person field does not serialize and fails CI. Online identifiers
   are personal data (UK GDPR) even when public; the first leak into a CC0 DOI is
   irreversible, so the gate is fail-closed.

2. **Positive-only.** Evidaxis measures the growth of systems and of trust tools.
   It never ranks losers, publishes negative or accusatory scores, or maintains a
   public shame-board. A retired cohort becomes `superseded` with its growth
   history intact, not a "dead niche".

3. **Open by construction (CC0), training welcome.** Every computed fact, score,
   schema, and metadata field is released CC0. AI training and grounding are
   explicitly welcome, not merely tolerated. Third-party raw content is never
   redistributed; only its hash and an archive pointer are kept. CC0 is
   one-directional and permanent; changing it later is a breach of trust.

4. **The archive is the moat, and it is never rewritten.** Point-in-time
   observations are append-only. Corrections add a new layer (errata), they never
   overwrite the original, which stays addressable. What byte-freeze protects is
   the **promise of the canon** ("a non-reconstructable snapshot of ascension by a
   dated, declared method"), not any single CSV column: the measured substrate may
   evolve by methodology version, the promise may not.

5. **Prediction is private (HYBRID).** The public surface is the archive (the
   moat). Any forward hypothesis is a private, pre-registered, commit-reveal
   record: its hash is published to prove priority, its content stays sealed until
   it resolves. Evidaxis makes no public actionable prediction.

6. **Canonical continuity survives the steward.** The record is anchored and
   byte-reproducible from public inputs, so its past integrity does not depend on
   any living person. A successor who keeps CC0 and positive-only continues the
   canon; any fork that abandons either invariant is, by this rule, non-canonical.

## Anti-roadmap (Evidaxis will NEVER, absent a constitutional amendment)

The most important roadmap is the list of things this project will never become.

- Rank, score, or profile natural persons.
- Publish negative, accusatory, or "worst of" signals.
- Sell pay-to-improve placement, sponsored placement, or any paid inclusion.
- Apply undisclosed manual overrides to inclusion or scores.
- Change the scoring methodology without a logged, versioned, public changelog.
- Delete or rewrite history retroactively for convenience (only legal or privacy
  removal via a tombstone that preserves the fact-of-existence).
- Publish investment recommendations or claim to predict winners publicly.
- The founder does not trade AI-related assets, nor advise others, on the basis of
  any private Evidaxis hypothesis. (Private forward hypotheses are treated as
  material non-public information and firewalled from any market action.)

## Amendment rule

An invariant or anti-roadmap item changes only by: (1) a public written proposal
stating the reason and which invariants it touches, (2) a 30-day freeze period,
(3) a signed decision (block-zero key), (4) a public changelog entry. No silent
change is valid. A change that violates Invariant 3 or 6 is not an amendment, it
is a fork, and the fork is non-canonical.

## Canonical reference

Claims and records are addressed by a stable identifier that is independent of any
single delivery format or URL scheme (see `CLAIM-URN.md`). This is what lets
citations survive a change in how machines retrieve the archive over a 10 to 15
year horizon.
