# Frozen web unit archive

Run `node web/scripts/make-test-fixture.mjs` from the repository root to regenerate
`2026-10-17/`. The generator uses only Node's standard library. It replaces that
one generated directory; identical repository inputs produce identical bytes.
Regeneration is an explicit maintenance action, never part of the test harness.
Commit the generated tree together with intentional fixture changes.

The selection includes real entity IDs named in unit tests and their JSON goldens,
plus deterministic samples of statuses, axis coverage, ownership and cohorts.
Pending owner transitions and dated collection gaps are retained. `selection.json`
records the selected IDs and snapshot dates. Synthetic test IDs without a real
archive record are supplied by the tests themselves.

All snapshots through 2026-10-17 are reduced to the selection, along with their
provenance and dropped lists. Counts describe the reduced snapshot. Source scores,
thresholds and methodology are unchanged; cohort summaries are computed over the
fixture members. Snapshot identity metadata is retained to exercise the loaders;
SHA256SUMS are regenerated for the fixture files, not production attestations.

History and observation rows are restricted to selected entities and capture (or
backfill computation) dates through 2026-10-17. Daily deps files are needed only on
snapshot dates; other daily captures remain in per-entity deps history. Deps rows
retain every field read by the loaders, omitting unused HTTP receipt metadata.
Daily raw provenance, HTTP bodies and unrelated datasets are not copied. Registry
files and dependency pins are filtered to the selected repositories.

`npx vitest run` always uses this tree. Loader helpers, native worker fs reads
(including promises and require), and Vite file imports reject repository live
`data/` and `etl/` paths, including symlinks and traversal. Tests over the full live
archive belong in `*.data.test.ts` and run with `npm run test:data`. Both suites run
before production build/checks in `npm run verify`. Existing 60-second timeouts
remain unchanged.

This directory is outside Astro's public assets. Production Astro configuration
and check-dist reject either data or ETL environment variable targeting this tree.
Check-dist's privacy registry always comes from repository `etl/`.

Before writing any output, the generator replaces personal account owners,
repository locators, homepages and package names with deterministic synthetic
values. Registries, snapshot/provenance references, pins and observation history
share the same replacements, including encoded URLs and former personal owners.
The replacement dictionary exists only in memory. Organization and approved
project-account identities may remain. Fixture SHA256SUMS cover the anonymized
bytes. The data suite scans every fixture file against the live personal-owner
registry; unit tests exercise cross-file locator consistency with invented input.

The shared unit preload also guards copy/cp sources, metadata reads and watches.
Node children and grandchildren receive the preload even with an explicit env;
fixture-reading scripts remain supported. Shell/non-Node children and --require
preloads are rejected because they can execute before the guard. Integration
scripts requiring those operations belong in the data suite. Production checks
resolve effective default paths as well as environment overrides, so a default
live-directory symlink into this fixture tree is rejected too.
Native fs.glob traversal is rejected because wildcard expansion can visit live
subdirectories internally; tests can use guarded readdir on fixture directories.
