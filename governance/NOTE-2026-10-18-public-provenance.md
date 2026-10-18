# Public projection of archived provenance

The website previously passed each archived `provenance.json` through unchanged.
Its `source_manifest.github_repos` included historical personal repository-owner
handles, including entries still classified `User` in `etl/owner_types.json`.
This conflicted with Constitution invariant 1 on the public website.

The website now applies `person_free_provenance_1` to every dated provenance
route. It publishes numeric GitHub repository references (`gh:<repo_id>`) in
place of repository slugs, retains GitHub weekly counts and OpenAlex annual
counts, and omits paper titles, authors and unlisted capture text. Missing
repository identity classification fails the build. `archive_sha256` identifies
the original provenance bytes, not the public JSON projection.

This changes publication only. Original snapshot bundles, their SHA256SUMS,
snapshot IDs, methodology and measurements remain unchanged in git, including
the genesis deposit (invariants 4 and 6). For checksum verification, download
the canonical files from `data/snapshots/<date>/` in the git archive. Website
snapshot and provenance projections intentionally differ from those bytes.

The dist privacy guard checks provenance for every date, including personal
owners of departed repositories no longer in the current ID map. The existing
raw-artifact handling of manifest, dropped lists and SHA256SUMS is unchanged.
This note does not claim those other artifacts or historical git files are
person-free. Regressions exercise all archived provenance routes, retained
measurements and hashes, fail-closed classification, and injected former and
departed personal handles.
