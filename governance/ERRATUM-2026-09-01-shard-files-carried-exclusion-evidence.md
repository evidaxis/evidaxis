# Erratum: sharded deep-check files carried exclusion evidence into the public tree

> dated 2026-09-01 · scope: the public repository tree, 2026-08-03 to 2026-09-01
> supersedes nothing; it records a defect and its remedy, per drift-never-amends.

## What the policy says

The census publishes **admitted members plus aggregate exclusion counts**, never
a per-repository negative judgment (positive-only discipline, I1). The rule was
made operational on 2026-08-03 after red-team finding #13 and written into
`.gitignore` as `data/census/*/deepcheck.jsonl`.

## What actually happened

The deep-check phase shards, and each shard writes its OWN file:
`deepcheck-0.jsonl`, `deepcheck-1.jsonl`, and so on. The ignore rule named the
single-worker file only, so every shard file was tracked and pushed. Twenty-four
such files from the August census entered the public tree: **64,776 rows,
157 MB, of which 60,678 concern repositories the census did NOT admit** —
licence, language, release and commit-history findings plus a README prefix per
repository. That is precisely the derived exclusion evidence the policy forbids
publishing.

The defect is in the rule's shape, not in anyone's judgment: a rule written for
one filename could not see a phase that renames its output per worker. The
census aggregates, the manifest and the tranche records were correct throughout;
no published measurement is affected, and no verdict changes.

## Remedy

1. The ignore rule now covers the shards (`data/census/*/deepcheck-*.jsonl`).
   The September shards were never committed.
2. The twenty-four August files are removed from the tree in the same commit as
   this record.
3. They remain in git HISTORY. Rewriting the history of a public repository that
   is mirrored elsewhere is an irreversible act with its own risks, so it is a
   decision for the keeper, recorded here as open rather than taken quietly.

## Open

- Whether to purge the August shard blobs from history (and re-anchor the
  mirrors), or to let the record stand with this erratum as the correction.
