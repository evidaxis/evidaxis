# Owner transfer confirmation (2026-10-04)

This record confirms the transfer of GitHub repository 299115429 from the
personal account `thomaspinder` to the organization `QuantClimate`, with
canonical name `QuantClimate/GPJax`. It follows the procedure in
`governance/OWNER-TRANSFER-2026-10-03.md` and changes publication metadata only,
not methodology, admission, measurements or historical observations.

## Evidence

- The weekly re-run of 2026-10-03 (Actions run 37158987047) stopped at the
  owner-publication refresh: `thomaspinder/GPJax: User to Organization transition
  requires manual confirmation`.
- GitHub GraphQL, queried on 2026-10-04 for all 5,937 cached repositories,
  resolved `thomaspinder/GPJax` to `QuantClimate/GPJax`, `owner.type:
  Organization`, repository ID 299115429, equal to the cached ID. It was the only
  User-to-Organization transition and no cached repository ID changed.
- [The organization endpoint](https://api.github.com/orgs/QuantClimate) reported
  name "Quant Climate", creation on 2025-06-07, three public repositories and
  website `https://quantclimate.com`.

## Changes

- `etl/owner_types.json`: entry `thomaspinder/GPJax` now has `owner_type:
  Organization` and `full_name: QuantClimate/GPJax`; key and `repo_id` unchanged,
  so the entity ID stays the same. Seeds and the ID map are untouched, so no
  discovery-frontier manifest is required.
- `web/src/data/person-free-handles.json`: `thomaspinder` added to the shared
  durable ban list before organization output is published.
