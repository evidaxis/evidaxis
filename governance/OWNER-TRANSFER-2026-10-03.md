# Owner transfer confirmation (2026-10-03)

This record confirms the transfer of GitHub repository 1129585228 from the
personal account `mensfeld` to the organization `coipond`, with canonical name
`coipond/coi`. It corrects publication metadata, without changing methodology,
admission, measurements or historical observations.

## Evidence

The maintainer supplied the following API observations for this confirmation:

- [The former repository endpoint](https://api.github.com/repos/mensfeld/code-on-incus)
  returned HTTP 301 to `/repositories/1129585228`.
- [The repository identity endpoint](https://api.github.com/repositories/1129585228)
  resolved to `coipond/coi`, with `id: 1129585228` and `owner.type: Organization`.
- [The organization endpoint](https://api.github.com/orgs/coipond) reported creation
  on 2026-07-01, four public repositories and website `coipond.ai`.

The numeric repository identity matches the previous cache. The old internal key
`mensfeld/code-on-incus` remains in the seeds, ID map and owner cache, preserving
entity `e_WJWEQY59YG9`. Changing that key would mint a different entity ID.
Only the cached `owner_type` and canonical `full_name` change.

The maintainer explicitly authorized this cache-only exception to the `etl/`
editing restriction. It does not authorize changes to frozen collector code,
seeds, identity mappings or archived bytes.

## Publication protection

`web/src/data/person-free-handles.json` is the shared durable ban list for web
publication, Card B, the dist guard and HF uploads. It preserves the existing
2026-07-10 protection floor and adds the prior personal owner. A transfer never
removes a handle from this list or weakens its matching to GitHub paths only.
Remove an entry only through a separate, deliberate review and dated record.

Web and HF projections publish `coipond/coi` and canonicalize a GitHub homepage
to `https://github.com/coipond/coi`. The numeric identity and internal key stay
unchanged. Future HF uploads reject the former personal handle even if the
owner cache no longer contains that account.

Raw verification artifacts under the site's snapshots routes are outside this
change. They retain the existing archive policy and may contain historical
repository keys; this record does not claim those artifacts are person-free.
Existing HF uploads are not rewritten by this change.

## Confirmation procedure for future User-to-Organization transitions

1. Resolve the old repository endpoint and the cached numeric identity endpoint.
   Record the redirect, canonical `full_name` and API `owner.type` in a new dated
   governance record. Confirm the destination is an Organization.
2. Require the returned repository ID to equal the cached ID. A different ID is
   an identity conflict, not an ownership confirmation; do not replace the cached
   ID to bypass the classifier's check.
3. Preserve the seed `github_repo`, ID-map key, entity ID and owner-cache key.
   Add each known prior personal owner to the shared durable ban list before
   approving public organization output.
4. With explicit authorization for the cache data edit, update only `owner_type`
   to `Organization` and `full_name` to the verified canonical name. There is no
   `--confirm` switch. The reviewed cache update is the confirmation; the refresh
   guard continues to reject unconfirmed transitions and identity mismatches.
5. Add regressions for refresh identity continuity, canonical repository and
   homepage projection, and continued rejection of the former personal handle.
6. Run `PYTHONPATH=. .venv/bin/pytest tests/ -q`,
   `.venv/bin/python collectors/owner_classify.py --verify`, and
   `cd web && npm run verify`. Check generated output outside `web/dist/snapshots`
   for the former handle. Then rerun the weekly workflow after the reviewed change
   is committed; do not suppress its refresh failure or keep an inaccurate User
   classification.

No discovery-frontier manifest is required for this confirmation: the seed
`github_repo` lines and tracked-system set do not change. Cache changes still
trigger Python CI, archive-integrity on main, and deployment checks. A cache-only
push does not directly trigger web-ci; the shared web data and regression changes
here do, and local web verification is required for future confirmations too.
