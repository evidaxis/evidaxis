# Public projection of archived drop lists

The website previously passed each archived `dropped.json` through unchanged.
On 2026-10-19, 6 of 19 dated files held 28 distinct repository addresses under
accounts still classified `User` in `etl/owner_types.json`. Those addresses sat
in `dropped[].github_repo`. This conflicted with Constitution invariant 1 on
the public website.

The website now applies `person_free_dropped_1` to every dated dropped route.
It keeps the drop record: `v`, `snapshot_date`, `checked_at`, `seeded`,
`in_snapshot`, `drop_fraction`, `max_drop_fraction`, and `note`. Each entry
keeps `entity_id`, `previously_tracked`, and `reason`. `github_repo` is
published as `repo_ref` (`gh:<repo_id>`). A repository absent from the owner
registry is published as `gh:unclassified`, and that gap does not stop the
weekly build. In `reason` and `note`, a User-type repository address is
replaced with the same `gh:<repo_id>` when the address is a registry key, a
registry `full_name`, or a github.com URL of that repository. Fields the
projection does not list are omitted. `archive_sha256` identifies the original
dropped bytes, not the public JSON projection.

This changes publication only. Original snapshot bundles remain unchanged in
git, including their dropped lists, SHA256SUMS, snapshot IDs and methodology
(invariants 4 and 6). For checksum verification, download the canonical files
from `data/snapshots/<date>/` in the git archive. The website projection
intentionally differs from those bytes.

New archive bytes are the subject of
`governance/AMENDMENT-PROPOSAL-2026-10-19-invariant-1.md`. This note does not
change that proposal, and it does not rewrite bytes already in git.

The dist privacy guard now checks dropped lists for every date, together with
a check that each built file carries `projection: "person_free_dropped_1"` and
does not carry a `github_repo` key. `manifest.json` and SHA256SUMS keep their
raw-byte exemption. This note does not claim those artifacts or historical git
files are person-free.
