# Erratum 2026-09-14: "byte-reproducible" survived on derived surfaces after the 2026-06-30 downgrade

> status: PARTIALLY FIXED 2026-09-14 · class: public over-claim in descriptions · found while
> preparing a catalog listing, whose draft repeated the claim; an independent second opinion
> flagged it before submission. No published value, score, snapshot or identifier changes.

## What the record says

Commit `24c19e8e` (2026-06-30) downgraded the site's reproducibility wording.
`etl/collect.py` writes `captured_at = now()` into `snapshot.json` and `provenance.json`, so
re-running the collector does not byte-reproduce those files (`AUDIT-BASELINE.md` §7). What is
invariant: `manifest_hash = sha256(source manifest)` and
`snapshot_id = sha1(methodology_version + manifest_hash)[:12]`. The public wording since then:
every score is checkable against its hash-pinned inputs, with raw provenance published.

## Where the old claim survived

| Surface | Wording | Status |
|---|---|---|
| `distribution/hf/README.md` (Hugging Face card) | "content-addressed (`snapshot_id` = payload hash) … byte-reproducible from public inputs". Two defects: the byte claim, and `snapshot_id` is not a payload hash | FIXED in the repository; live on Hugging Face from the next weekly upload |
| `README.md`, Principles | "Every score is byte-reproducible from the manifest." | FIXED |
| `awesomedata/apd-core` card, `academic/awesome-datascience` entry (third-party catalogs, merged) | "content-addressed and byte-reproducible from public inputs" | OPEN: one correction PR per catalog, spaced out |
| `CONSTITUTION.md`, Invariant 6 | "anchored and byte-reproducible from public inputs" | OPEN: an invariant changes only through the Amendment rule; not edited here |
| `genesis-deposit/*` | same phrase in frozen copies | NOT EDITED: frozen deposit |

`METHODOLOGY-VERSIONING.md` uses "byte-reproducibility" for the rule that published snapshots
are never retro-edited. That is a preservation property, true as stated, and is left unchanged.

## Correct wording

Scores and snapshot identifiers are checkable against hash-pinned inputs with raw provenance
published. Snapshot files carry their capture time, so their exact bytes are preserved and
anchored in git, not regenerated.
