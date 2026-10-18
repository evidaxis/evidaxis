# Pending owner-transfer confirmations (2026-10-18)

This review follows `governance/OWNER-TRANSFER-2026-10-03.md`. It records
available live REST evidence, but does not yet confirm the four cache changes.
The seed keys, ID map, entity IDs, owner cache and pending queue remain unchanged.

## Evidence observed on 2026-10-18

Each former repository endpoint returned `Moved Permanently` with the numeric
identity URL below. Each canonical repository endpoint returned the listed
`id`, matching both the cached `repo_id` and pending record, and
`owner.type: Organization`.

| Former endpoint | Redirect target | Canonical endpoint | Returned ID | Owner type |
| --- | --- | --- | --- | --- |
| [<former personal owner>/Codewhale](https://api.github.com/repos/<former personal owner>/Codewhale) | `/repositories/1137711311` | [codewhale-hq/Codewhale](https://api.github.com/repos/codewhale-hq/Codewhale) | 1137711311 | Organization |
| [<former personal owner>/opencrabs](https://api.github.com/repos/<former personal owner>/opencrabs) | `/repositories/1157543432` | [opencrabs/opencrabs](https://api.github.com/repos/opencrabs/opencrabs) | 1157543432 | Organization |
| [<former personal owner>/pipelock](https://api.github.com/repos/<former personal owner>/pipelock) | `/repositories/1152497359` | [pipelab-org/pipelock](https://api.github.com/repos/pipelab-org/pipelock) | 1152497359 | Organization |
| [<former personal owner>/AutoSci](https://api.github.com/repos/<former personal owner>/AutoSci) | `/repositories/1206036567` | [DAIR-AutoResearch/AutoSci](https://api.github.com/repos/DAIR-AutoResearch/AutoSci) | 1206036567 | Organization |

The responses were read through the GitHub connector. Unauthenticated `curl`
in the execution environment failed DNS resolution for `api.github.com`.
The connector does not support direct `/repositories/<id>` requests, the web
reader could not access those URLs, and no browser was available. No direct
numeric-endpoint response is claimed here.

## Remaining decision and file changes

Step 1 of the confirmation procedure explicitly requires resolving the cached
numeric identity endpoint. Either obtain those four direct responses, or obtain
explicit authorization to accept the redirect target plus matching canonical
REST identity as equivalent evidence. That decision remains with the maintainer.
The previous User classifications continue to mask the owners in derived web
and HF projections; raw integrity artifacts retain their existing archive policy.

After that prerequisite is satisfied, add the four former personal owners to
`web/src/data/person-free-handles.json` before approving organization output,
then change only `owner_type` and `full_name` in the four existing
`etl/owner_types.json` entries. Preserve each key and `repo_id`, seeds and ID map.
Add the procedure's continuity, canonical repository/homepage and durable-ban
regressions, and run its required verification. The existing refresh removes
confirmed entries from `etl/owner_transitions_pending.json`; it does not need a
manual queue rewrite. A new dated confirmation record must cite this review.

Rerunning the weekly workflow after the reviewed change is committed remains
a maintainer action. This review makes no historical archive or methodology
changes and authorizes no release-path changes.

## Direct identity check, 2026-10-18 21:40 UTC

Resolved `GET /repositories/<id>` with an authenticated GitHub API client:

| Cached ID | Canonical full_name | owner.type | archived |
|---:|---|---|---|
| 1137711311 | codewhale-hq/Codewhale | Organization | false |
| 1157543432 | opencrabs/opencrabs | Organization | false |
| 1152497359 | pipelab-org/pipelock | Organization | false |
| 1206036567 | DAIR-AutoResearch/AutoSci | Organization | false |

Steps 1 and 2 of the confirmation procedure hold for all four: each returned ID
equals the cached ID and each destination is an Organization. Steps 3 to 6 (ban
list, cache edit, regressions, verification) are scheduled after the 2026-10-24
release, because the cache edit touches the weekly collection path during its
pre-release freeze. Until then the four systems stay masked, which is safe.
