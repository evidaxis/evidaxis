# Governance act: AI-v1 shadow layer

> status: **FIXED 2026-08-03**. Implements the non-public shadow obligation in
> `REGISTRY-GROWTH-POLICY-2026-07-21.md` under the frozen enumeration procedure
> of `CENSUS-AI-V1-PREDICATE-2026-08-03.md`. This act changes no public
> admission rule and creates no public membership judgment.

## 1. Operative rule

Once each week, cloud Actions enumerate the full GitHub Search universe
`stars:200..499 fork:false is:public`. Enumeration uses geometric star bands,
creation-timestamp slicing at the 1000-result cap, rejection and retry of
`incomplete_results`, and a fail-closed per-band coverage assertion. Surplus
rows caused by a moving index are retained in the aggregate partition ledger
as `index_drift`; a short band is retried three times and then aborts.

The destination is a PRIVATE repository in the Evidaxis organization. The
public repository contains the method and workflow, never the observations.

## 2. Stored bytes

Each repository observation has exactly three fields:

```
{"id": <numeric GitHub repository id>, "stars": <integer>,
 "observed_at": <UTC timestamp>}
```

No owner, name, handle, URL, description, topics, language, licence, code,
release, package, commit, contributor, activity, classifier output, or
predicate verdict is queried as a shadow signal, evaluated, or retained.
GitHub Search returns service-defined repository objects; the collector
discards their incidental fields before the first per-repository write. Dated
partition ledgers contain only query boundaries, counts, retries, completion
state, and index drift; they contain no repository labels or extra
per-repository attributes. Every dated snapshot has a SHA-256 anchor.

## 3. Non-publication

The shadow band is below the public 500-star bar. An observation is therefore
neither an admission nor an exclusion and must never become a site card,
pending-manifest row, public dataset row, feed item, or named public judgment.
Its sole purpose is early point-in-time raw material for a possible future
private data product. Crossing 500 stars does not publish the private history;
public admission remains governed by the monthly AI-v1 predicate.

## 4. Retention and upgrade path

Completed snapshots, hashes, and partition audits are append-only and retained
indefinitely in the private repository. A failed run retains its minimal
checkpoint until a later run completes the same UTC date; successful completion
removes that checkpoint. No historical snapshot is enriched in place.

Any schema expansion, finite retention schedule, use in a private product, or
change of access boundary requires a new dated governance act. A successor
schema preserves these v1 bytes unchanged and writes a separately versioned
series. This act does not authorize publication now or later.

## 5. Operator configuration

The public repository must define the Actions variable
`EVIDAXIS_SHADOW_REPO` as the initialized private repository's `owner/name`.
It must also define exactly one operator-created Actions secret:
`SHADOW_REPO_TOKEN`, a fine-grained token limited to that private repository
with Contents read/write permission. GitHub's native workflow token needs no
operator creation and is not used to write the shadow repository. The workflow
verifies PRIVATE visibility before collecting and fails non-zero on every
collection, validation, commit, or push error.
