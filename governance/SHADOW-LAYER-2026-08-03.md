# Governance act: AI-v1 shadow layer

> status: **FIXED 2026-08-03; operational design amended 2026-08-03**.
> Implements the non-public shadow obligation in
> `REGISTRY-GROWTH-POLICY-2026-07-21.md` under the frozen enumeration procedure
> of `CENSUS-AI-V1-PREDICATE-2026-08-03.md`. This act changes no public
> admission rule and creates no public membership judgment.

## 1. Operative rule

The shadow layer separates discovery from observation because they answer
different questions and have different costs.

Once each month, `shadow-discover` enumerates the full GitHub Search universe
`stars:200..499 fork:false is:public`. Eight Search shards use geometric star
bands and creation-timestamp slicing at the 1000-result cap, reject and retry
`incomplete_results`, and retain the existing fail-closed per-band coverage
assertion. Each completed shard is committed independently. The merge fails
non-zero and names every missing shard before it can create the monthly identity
set. Only one discovery shard runs at a time because all jobs share the same
30-request-per-minute Search budget; this also leaves at most one uncommitted
shard if a job reaches its timeout.

Once each week, `shadow-observe` reads the newest complete monthly identity set
and refreshes current stars with GraphQL queries of 50 aliased repositories.
Four observation shards divide that set exactly once. Each completed shard is
committed independently; the dated merge verifies complete identity coverage
before writing a snapshot and SHA-256 anchor. If no complete discovery set
exists, observation fails non-zero with an instruction to run
`shadow-discover`; an empty snapshot is never emitted.

Every shard emits `repos completed / repos total` progress at start, finish, and
at intervals no longer than approximately 60 seconds while work is in flight.

## 2. Measured reason for two cadences

The first live single-job design ran for 2 hours 57 minutes, was cancelled, and
left the private destination empty because it emitted only after the full Search
sweep. The 200..499 band measured 146,589 repositories. That is larger than the
121,044-repository public >=500 census, whose Search enumeration took about five
hours locally at the 30-request-per-minute ceiling. A clean weekly six-hour job
with no cross-run resume could therefore expire and restart from zero forever.

Monthly discovery removes that repeated Search cost. Weekly observation is
approximately 146,589 / 50 = 2,932 one-point GraphQL queries. With four shards,
it is latency-bound and scales linearly rather than approaching the Search
ceiling.

## 3. Stored bytes

Discovery shard files and `discovery/<YYYY-MM>/ids.jsonl` contain exactly:

```
{"id": <numeric GitHub repository id>, "full_name": <repository address>}
```

`full_name` exists only to address the repository during a later GraphQL
observation. It is never copied into an observation row.

Observation shard files and
`observations/<YYYY-MM-DD>/snapshot.jsonl` contain exactly:

```
{"id": <numeric GitHub repository id>, "stars": <integer>,
 "observed_at": <UTC timestamp>}
```

The only other retained files are SHA-256 anchors for the merged identity set
and dated snapshot. No owner field, handle field, URL, description, topics,
language, licence, code, release, package, commit, contributor, activity,
classifier output, predicate verdict, Search response, GraphQL response, or
partition checkpoint is retained. Incidental API fields are projected away
before the first per-repository write. Temporary Search coverage ledgers and
checkpoints exist only inside the disposable runner checkout and are removed
before a shard can be committed.

## 4. Non-publication

The shadow band is below the public 500-star bar. Discovery identity and a star
observation are therefore neither an admission nor an exclusion and must never
become a site card, pending-manifest row, public dataset row, feed item, or named
public judgment. Their sole purpose is early point-in-time raw material for a
possible future private data product. Crossing 500 stars does not publish the
private history; public admission remains governed by the monthly AI-v1
predicate.

## 5. Retention and upgrade path

Completed shards, merged identity sets, dated snapshots, and hashes are
append-only and retained indefinitely in the private repository. A timed-out or
failed runner loses only its uncommitted shard checkpoint; already completed
shards remain available to a rerun. No historical identity set or observation
is enriched in place.

Any schema expansion, finite retention schedule, use in a private product, or
change of access boundary requires a new dated governance act. A successor
schema preserves these bytes unchanged and writes a separately versioned
series. This act does not authorize publication now or later.

## 6. Operator configuration

The public repository must define the Actions variable
`EVIDAXIS_SHADOW_REPO` as the initialized private repository's repository
address. It must also define exactly one operator-created Actions secret:
`SHADOW_REPO_TOKEN`, a fine-grained token limited to that private repository
with Contents read/write permission. GitHub's native workflow token needs no
operator creation and is not used to write the shadow repository.

Both workflows assert PRIVATE visibility before any write. Every collection,
validation, merge, commit, and push error exits non-zero. The monthly schedule
runs on day 3 at 02:11 UTC; the weekly schedule runs Sundays at 05:43 UTC and
does not collide with the existing Saturday weekly snapshot.
