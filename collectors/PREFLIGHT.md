# Weekly archive integrity

The weekly workflow runs `python3 collectors/preflight.py` before warming GitHub
statistics or collecting a snapshot. It refreshes metadata for every seed in
GraphQL batches, sharing that cache with collection and owner classification.
Only unresolved GraphQL entries fall back to REST. A GraphQL null alone never
becomes a departure record.

The report is saved to `$EVX_GH_CACHE_DIR/preflight.json` (the shared temporary
cache by default) and uploaded as the `preflight-report` workflow artifact even
when the check fails. All new moves, owner-type changes, identity mismatches,
confirmed REST 404/410/451 responses and other errors are reported together.
The check fails before collection if any remain, including during a dry run.
Confirmed canonical aliases in the owner registry are not new moves.

Preflight never changes seeds or confirms ownership transitions. Review its
report before preparing changes under the repository's freeze rules. To record
reviewed departures from that report:

```sh
python3 collectors/departed.py --input /path/to/preflight.json
```

This creates `data/observations/<date>/departed.json` exclusively, refusing to
overwrite an existing journal. Each row contains `date`, `github_repo` and the
observed `github_status`. Record all departures for that day together. A 404
records what GitHub returned with the collection credentials; it does not prove
permanent deletion. Redirect statuses 301/302/307/308 can also be recorded when
separately observed; a GraphQL canonical-name change is not evidence of an HTTP
redirect status.

`universe_integrity.py --base <tree-or-commit> --head <tree-or-commit>` compares
seed sets, ignoring order, case and cosmetic changes. Each removed repository
needs a matching record in a newly added departure journal in the same range.
A discovery manifest cannot excuse a removal. Additions still require a newly
added dated discovery-frontier manifest; mixed changes require both. Existing
departure journals cannot be modified, deleted or reused for a new removal.
The retrospective September 26 and October 3 records cite existing commits and
do not claim a new network observation.

The website's archived `provenance.json` is a public projection. It retains
numeric measurements and source references (`gh:<repository-id>`), omits raw
repository slugs and paper titles, and carries `archive_sha256` for the original
provenance bytes. The git snapshot bundles and their SHA256SUMS remain unchanged.
Use the git archive files for checksum verification. The dist privacy guard now
checks public provenance for every date, including departed owners; manifest,
dropped lists and SHA256SUMS retain their existing raw-artifact exemption.
