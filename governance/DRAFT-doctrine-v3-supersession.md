# DRAFT — Dated supersession of the v3 HALT doctrine (decision-by-drift made explicit)

> status: ADOPTED 2026-07-11 with amendments (drift-never-amends + full-charter sweep) — see ADJUDICATION-2026-07-11.md §2
> Grounds: spine/PRE_INGEST_CONTRACT.md §1.1, §1.3, §10 · weekly-snapshot.yml +
> t2-daily-snapshot.yml crons · archive-integrity.yml genesis byte-identity check ·
> full-analysis map 2026-07-02, item 1 (grounded, refute-passed).

## The dead letter

PRE_INGEST_CONTRACT (spine artifact, "binding, effective immediately") demands:
- §1.1: "etl/collect.py MUST NOT run on a schedule/cron" + a `no-v2-production-accession`
  CI guard (grep over .github/workflows/ = 0 hits — the guard was never built);
- §10: the genesis DOI "is reserved for the first v3 signed snapshot".

Reality, running weekly since 2026-06-28 and enforced by the institute's own CI:
- weekly-snapshot.yml (cron) + t2-daily-snapshot.yml (cron) run the v2 line live;
- 19→134 systems accessioned under v2/m2 — the v2 series IS the cited canon;
- DOI 10.5281/zenodo.21076012 sits on the m1 genesis, and archive-integrity.yml
  enforces that THIS genesis stays byte-identical — the contract calls that snapshot
  "NOT the t=0 the institute cites".

The decision was already made — by drift. An integrity institute cannot carry a
binding contract its own crons violate weekly; a future auditor reading "binding,
effective immediately" must not be left to guess which text is alive.

## Supersession (forward amendment; append, never rewrite)

Effective on keeper signature:

1. **The v2/m-methodology line is the canonical cited series of record.** Its
   snapshots, DOIs, URNs and history are the institute's public canon (this matches
   IDENTITY.md and every published citation surface).
2. **PRE_INGEST_CONTRACT §1.1 and §1.3 (HALT clauses) and §10 ("genesis DOI reserved
   for first v3 snapshot") are SUPERSEDED as of the signature date.** The clauses stay
   readable in place; a forward amendment block in PRE_INGEST_CONTRACT.md points here.
3. **The spine is re-scoped from "replace v2" to "graft onto the live lineage".**
   Spine artifacts remain the design authority for the data model; their authority
   over SEQUENCING the live line passes to the quarantine-funnel rule (see
   DRAFT-m3-quarantine-adjudication.md).
4. The genesis DOI keeps exactly its factual meaning: the immutable m1 seed deposit
   of 2026-06-27 — the first stone, not the reserved future.

## Why this is governance, not paperwork

Invariant 4 protects "the promise of the canon". A binding internal contract that
contradicts the published canon is a live threat to that promise: it licenses a future
steward (or auditor) to declare the real series non-canonical on textual grounds. One
dated signature closes the gap the cheap way — before it compounds (CP-6 class debt).

## Keeper action

- [ ] Sign (date + initials or block-zero signature note): ______
- [ ] Amend PRE_INGEST_CONTRACT.md with the forward block referencing this file
      (one commit, both files together).
