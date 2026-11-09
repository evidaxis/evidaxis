# Person-free publication classifier, 2026-11-09

This corrects publication privacy under invariant 1. It does not change scores,
axes, thresholds, historical captures, project-account decisions, canary
assignment or control-shell checks. The November switch date is unchanged.

## Rules

The source of truth is `scripts/person_free.py:classify_registry` and its JS
counterpart `web/src/lib/personFree.mjs:classifyRegistry`. Each accepts a
registry, project accounts and a durable floor. Each returns personal handles,
public organizations, personal paths, stale personal paths, canonical public
paths and public repository keys. Classification does not modify its inputs or
persist an identifier index.

- **a:** A current Organization owner is public. This takes precedence over
  another User row or a floor entry for the same login.
- **b:** Current User owners are personal, except recognized project accounts.
- **c:** Every former owner after an owner change is personal unless currently
  known as a public organization or project account. Historical owner types are
  not inferred or stored.
- **d:** The old path of a transfer is personal when either endpoint is personal.
  It is matched exactly, with the existing canonical-path substring exemption.
- **e:** An organization-to-organization path is not personal when the former
  organization remains public in the registry.
- **f:** Standalone word matching requires at least four characters and excludes
  numeric handles. Distinctive words found in the site's template source require
  GitHub context. Short and numeric exact field values remain masked. Explicit
  mentions, GitHub URLs, Pages hosts and raw-content URLs remain detectable.
- **g:** The same classification feeds names, slugs, repository labels and links,
  package labels, homepages on any host, nested free text and dropped records.
  A former owner's homepage is subject to the same mask as a current owner's.
- **h:** Website and HF privacy findings report the artifact path, `rule=f` or
  `rule=d`, and eight hexadecimal digest characters. A random process-local salt
  is neither persisted nor printed. If the artifact path reveals the identifier,
  its path is hashed too. Repeated findings within a process are correlatable;
  the same value in another process has a different digest.

The source vocabulary is computed from non-test Astro/TypeScript source, not
from owner data. Its source root remains the same when Astro bundles modules.
The floor file and frozen registry are not rewritten.

## Consumers

All eight locations from the systemic review use the shared classifier, directly
or through the shared classification/index accessor:

1. Python `load_handle_index`, publication projection and HF guard.
2. JS `personalOwnerHandles` and `personalStalePaths` compatibility accessors.
3. The website mask in `person_free.ts`, including homepage and nested text.
4. `check-dist.mjs`, including archived provenance and exact stale paths.
5. `public_dropped.ts` and its repository/text maps.
6. The live-archive assertions in `public_dropped.data.test.ts`.
7. `person_index_build.py` registry and current-owner adapters.
8. `fixture-privacy.mjs`, including former-owner inputs and organization precedence.

Archive loading applies the nested text mask before HTML/feed consumers see the
entities. Card B consumes `publicOwnerType` for API links instead of deciding
from a raw `owner_type` field.

The single-source guard detects raw owner-type comparisons, membership tests
and aliases, including multiline JS decisions. It does not ban using a result
already returned by the classifier. Its exceptions are the two shared modules,
the registry collector, and the rehearsal's independent mutation oracle.

Five initial findings were false positives: workflow `actor.type` in
`release-scorecard.mjs`; two JSON-LD branches on `publicOwnerType`; the Card B
branch on that same public result; and the `owner_types_1` schema-version check.
The guard now distinguishes raw owner-type data from metadata and shared results.
There are no file-wide exemptions for these consumers. Comment stripping keeps
URLs and line breaks; schema key lists are not treated as raw owner values.

## Verification

Shared fictional vectors cover live organizations transferring one repository,
person-to-person transfers, organization renames with unknown former type,
transfers between live organizations, project accounts, case, short/numeric
handles, template words, the floor and encoded former-owner homepages.

The required Python suite, JS conformance suite and all web unit tests pass.
The index-builder tests and the Zenodo stage tests also pass. Three live data
test files exercise dropped/provenance projections and the actual `check-dist`
process, including absence of identifiers from diagnostics. HF dry-run on
2026-11-07 projects 6,682 entities with zero guard findings.

Four source mutations were applied and restored byte-for-byte:

1. One wrong vector expectation fails both Python and JS conformance.
2. A raw `entry.owner_type === 'User'` in `hubs.ts` fails the single-source guard.
3. Replacing the website handle index with current owners only fails the
   person-to-person former-homepage experiment.
4. Removing organization precedence fails both language suites and the
   live-organization transfer experiment.

These are local mutation checks with independent vector expectations. The full
candidate `benign_all` replay, leak drills, complete `npm run verify` and dist
SHA comparison belong to the orchestrator's subsequent acceptance run.

## Expected dist changes on this checkout

An in-memory comparison of the HEAD and working-tree projection functions on
the same live archive finds additional masking for `e_RYZNSTS8RB1` and
`e_YCSQMCVD2PT`. Both names/slugs become neutral; the latter also loses its
revealing repository name/label. Across seven snapshots there are 12 changed
entity rows, and five of those also change the repository projection. There
are no dropped-record projection differences on these inputs.

Expected surfaces are the two entity HTML/JSON records, their badge HTML/SVG
outputs, `search-index.json`, `llms.txt`, the unassigned-cohort JSON/CSV tables,
and the affected dated `snapshot.json` files. Card B exports, feeds, chart
accessibility text and any other materialization that includes the changed
names must follow the same mask. The two entities are outside the canary pairs.

The names move in alphabetical order. Comparing the source pagination inputs
predicts these additional HTML changes (page 1 means `index.html`; other pages
mean `page/<n>/index.html`):

| Route base | Pages |
| --- | --- |
| `snapshots/2026-09-26/` | 18 through 26 |
| `snapshots/2026-10-03/` | 18 through 26 |
| `snapshots/2026-10-10/` | 1 through 28 |
| `snapshots/2026-10-17/` | 1 through 28 |
| `snapshots/2026-10-24/` | 1 through 28 |
| `snapshots/2026-10-31/` | 1 through 28 |
| `snapshots/2026-11-07/` | 2 through 29 |
| `ai/cohorts/unassigned-v1/` | 1 through 29 |
| `coverage/` | 2 through 29 |

The seven listed snapshot directories also change `snapshot.json`. Pagination
changes include neighboring rows shifting between pages, not new measurements.
This is a projection/source audit, not a completed dist build comparison.
The orchestrator must reconcile the actual file hashes with these causes.
