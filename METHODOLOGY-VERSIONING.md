# Methodology versioning — the immutable-score contract

> created: 2026-07-02 · status: contract (binding) · provenance: build-once integrity contract; continuity-invariant deliberations (internal records)
> Public registry source: [`web/src/lib/methodology-registry.json`](web/src/lib/methodology-registry.json), served at `/methodology-registry.json` (route `web/src/pages/methodology-registry.json.ts`) and consumed by the JSON-LD builders and methodology pages.
> Reference: this generalizes the private spine `MethodologyRegistry` schema; the public registry carries the public fields only.

## The invariant this locks

A published Evidaxis score means "this system measured *this* under methodology
*M* at epoch *T*". If the meaning of *M* can drift, then every citation frozen
into a model's weights silently rots. So the methodology is treated exactly like
the data: **append-only, content-addressed, never silently recomputed.**

This is the methodology half of the same continuity guarantee the claim-URN makes
for references ([CLAIM-URN.md](CLAIM-URN.md)): the URN binds a claim to a
`methodology_version`, and this contract guarantees that version resolves, forever,
to one exact definition.

## Rules

1. **A version is content-addressed.** Each entry in the registry carries a
   `formula_fingerprint` (sha256 of the canonical axes+gate definition) and a
   `code_commit`. The version string (`m1`, `m2`, ...) is a handle onto that
   tuple, not a label pointing at nothing. Any CC0 consumer can rebuild a score
   from the pinned inputs against the exact methodology it was computed under.

2. **Immutable, append-only.** A methodology change is a NEW version on a NEW row.
   An existing row is never edited. Its `formula_fingerprint`, `code_commit`, and
   `effective_at` are frozen the moment it is published. The genesis version (`m1`)
   is additionally frozen by the Zenodo genesis DOI.

3. **No silent recompute.** Old scores are never recomputed under a new
   methodology. When the formula changes, the old snapshots keep their old
   `methodology_version` and their old numbers; new snapshots carry the new
   version. Both remain simultaneously valid, each under its own method. A "fix"
   is `mN+1`, published forward, not a rewrite of `mN`.

4. **Version bump semantics (SemVer-shaped).** The registry uses a single integer
   `mN`, but the *reason* is classified in the `changelog`:
   - **MAJOR** — the scoring semantics change (a threshold, an axis definition, the
     gate). Example: `m1 -> m2` raised the rising threshold from `z >= 0` to
     `z >= 1` and added a `cohort >= 5` floor (D10a).
   - **MINOR** — a new source or signal is added without changing existing scores.
   - **PATCH** — a bugfix that does not alter any already-published number.
   Every bump, regardless of class, is still a new immutable row (rule 2).

5. **Readers MUST resolve old versions.** The site keeps an immutable, permalinked
   page per version (`/methodology/v1/` for `m1`, `/methodology/m2/` for `m2`, ...).
   These pages are never rewritten. `/methodology/current/` is a stable alias that
   canonicalizes onto the active version's permalink; it is the only methodology
   URL whose target moves. JSON-LD `measurementTechnique` on a record resolves via
   the record's own `methodology_version` to that version's permalink.

6. **`/methodology/current/` never strands a citation.** Because a record cites its
   own version (URN + `methodology_version` field), following `current` is only a
   convenience; the durable link is always the versioned permalink.

## As-of resolution

Given a `methodology_version` from any record (or the epoch segment of a
claim-URN), the registry resolves it to `{formula_fingerprint, code_commit, page,
effective_at}`. That tuple is sufficient to (a) locate the human definition
(`page`), (b) verify the code that produced it (`code_commit`), and (c) confirm the
definition has not drifted (`formula_fingerprint`). The `effective_at` field
supports as-of queries: which methodology was current at epoch T.

## Current state

| version | status | rising threshold | cohort floor | page | frozen |
|---|---|---|---|---|---|
| `m1` | superseded | `z >= 0` | none | `/methodology/v1/` | genesis DOI `10.5281/zenodo.21076012` |
| `m2` | current | `z >= 1` | `>= 5` members | `/methodology/m2/` | commit `24e0fd4` |

`m1` scores (genesis snapshot, 2026-06-27) stay valid under `m1`; they are not
recomputed under `m2`. New snapshots are computed under `m2`.

## Seam rule — provisional snapshots and the Type-2 layer (dated 2026-07-02)

Two clarifications that close open seams in the pre-spine interim, forward-only:

1. **`provisional: true` is an immutable historical fact.** Published snapshots
   carrying the pre-spine provisional flag are never retro-edited to "close"
   the seam (that would break byte-reproducibility, rule 3). Spine-completeness
   is asserted only FORWARD: by later snapshots and/or a signed event. A reader
   evaluating an old snapshot reads the flag as "provisional at publication
   time", not as a live status.

2. **`data/observations/` is a forward Type-2 layer, not a pre-spine prelude.**
   Daily point-in-time captures (watchers, open issues, dependents) are
   first-class, un-backfillable observations; each row's custody claim is valid
   from that row's own `captured_at`. Any future scored axis built on this
   layer (e.g. the deps.dev dependents candidate) versions forward like every
   methodology change; the captured history itself carries no provisional
   discount.

## Errata (documentation-only; frozen files are never edited)

- **2026-07-02 — `etl/collect.py` header docstring lags m2.** The module
  docstring (lines 10-11) still describes the gate in m1 language ("raw slope > 0
  AND cohort-z >= 0"). The *executable* code enforces m2: `RISING_Z_FLOOR = 1.0`
  and `MIN_COHORT_FOR_BADGE = 5` (both marked "D10a fix" inline, and
  `METHODOLOGY_VERSION = "m2"`). The file is byte-frozen post-genesis (its m1
  ancestor is certified by the genesis DOI; the live copy is pinned by the `m2`
  registry row's `code_commit`), so the stale prose is corrected here in words,
  not in the file. An auditor reading the docstring literally should trust the
  constants and the registry, which agree with each other and with the
  published snapshots.
