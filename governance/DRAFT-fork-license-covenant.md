# DRAFT — Fork-license covenant (making the canonical-fork rule bite without a legal entity)

> status: ADOPTED 2026-07-11, renamed Canonicity Policy (+equivocation-freeze, citation-surface rule) — see ADJUDICATION-2026-07-11.md §5
> Grounds: TRUST-ROOT canonical-fork rule · LICENSING.md dual-track (repo Apache-2.0,
> data CC0) · CONSTITUTION Invariant 6 (continuity) + amendment rule (fork clause).

## The problem with the current rule

The canonical-fork rule lives in prose ("a successor must keep CC0 + positive-only").
CC0 data is, by design, unconditionally reusable — we cannot and must not restrict the
DATA. What CAN carry the covenant are the assets that are NOT CC0: the name, the
trust-root lineage (KeyRegistry), the code license, and the citation surfaces.

## Covenant (proposed)

1. **Data stays CC0, unconditionally.** Nothing here restricts reuse of any byte of
   the archive. A hostile fork may copy everything — that was always the deal, and it
   is a feature (the moat is the accumulated LINEAGE, not the bytes).
2. **The name is the license's hostage.** "Evidaxis" (name, logo, domain, org handles)
   is NOT granted by any code or data license. A fork that keeps CC0 + positive-only
   may STATE its derivation ("derived from the Evidaxis archive, DOI …") but may not
   present itself AS Evidaxis without a signed succession event
   (DRAFT-succession-lock.md).
3. **Code license stays Apache-2.0** (patent grant, attribution) — forks keep
   NOTICE; the NOTICE file names the canonical archive DOI, so every code fork
   mechanically carries a pointer back to the true lineage.
4. **Trust-root lineage is unforkable by construction:** anchors chain to the
   block-zero key; a fork can copy history but cannot extend the signed chain. The
   covenant makes this explicit as the PUBLISHED test of canonicity: "check the
   KeyRegistry chain" is the one-line answer to "which fork is real?"
5. **Non-canonical forks are not enemies** (positive-only extends to forks): the
   institute never publishes a fork shame-list; it publishes only the POSITIVE test
   of canonicity (the chain), letting verification do the talking.

## What this deliberately does NOT do

No trademark filing is claimed until one exists (no theater); no CLA; no restriction
on the data. The covenant's teeth = name + signed lineage + NOTICE pointer, all of
which exist today.

## Keeper action
- [ ] Adjudicate; if adopted, append pointer into LICENSING.md + NOTICE (one commit).
