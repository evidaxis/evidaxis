# Growth policy amendment — the weekly +6% activation rate is revoked (2026-09-20)

> status: FIXED 2026-09-20. Amends `REGISTRY-GROWTH-POLICY-2026-07-21.md`, which is
> retained unchanged as the record of what was decided on 21 July. Effective for the
> first tranche run after the capacity measurement named below reports.

## What is revoked

One clause of the 21 July policy, quoted in full:

> **Crawl-budget discipline — geometric weekly activation (founder, 2026-07-21):**
> the wave publishes the MANIFEST at once (a machine-readable membership file, not
> pages); CARDS go live WEEKLY at **+6% of the current live-card count** (floor:
> 10/week; cap: the available pending queue). Rationale: a constant RELATIVE rate
> reads as organic growth to crawlers (no step-bursts), and the absolute tranche
> scales with the domain's own maturing crawl budget … A sudden burst of thousands
> of templated URLs on a fresh domain is a programmatic-SEO spam pattern; geometric
> activation with history-rich cards is healthy catalog growth.

## Why it is revoked

**The rationale was written as an established fact and is not one.** No published
search-engine rule sets a safe publication rate, and no measurement of this registry
supports the specific figure of 6%. Search guidance defines mass-produced spam by the
purpose of the pages and their value to a reader, not by how many appear in a week.
The clause is therefore a precautionary hypothesis of 21 July, recorded here as such:
not a measured limit, and not a requirement imposed from outside.

**Its cost was real and was being paid.** 201 cards are live against a pending
membership of 5,826 already published in the manifest. At +6% a week the queue drains
in about a year, while the systems in it stay unpublished — on a registry whose stated
value is completeness of membership.

**What the run actually costs was measured today**, which the 21 July decision never
did. On a random sample of the pending set: 2 GitHub REST calls and ~1 second per
repository, $0 in money; for all 5,826 that is ~11,700 calls, about 2.3 hours bounded
by the 5,000-per-hour rate limit. Reconstructing the pre-capture commit history of the
live cards took 10 minutes for 121 of them.

## What replaces it

**Activation is bounded by sustained servicing capacity, measured, not by a calendar
percentage.** A tranche may be as large as the registry can carry, where "carry" means
all of the following hold and are reported with the tranche:

1. The full daily observation cycle over the enlarged card set completes inside the
   declared refresh window and inside the platform's own limits, measured on a dry run
   at the intended size — not extrapolated from a one-off collection.
2. Every activated member still passes the unchanged quality gates. **Four weekly
   observations before a card is published stays exactly as it is**: four calls made
   over a few days do not satisfy it, and reconstructed history does not substitute for
   captured observations. A tranche activated today therefore publishes four weeks
   later, and that interval is a property of the evidence, not a throttle.
3. The membership predicate, the mechanical publication order, and the standing
   disclaimer that publication order is a schedule and never a measurement verdict are
   unchanged.

**Before the first tranche under this amendment**, one dry run of collection and site
build at the full intended size reports: request count, retries, wall time, memory,
completeness of results, and a check of URLs, canonicals and experiment-group
membership. If that run does not fit, the tranche is sized to what it shows, and the
figure is published with the tranche.

## What this amendment does not touch

The display experiment on the page template (24 matched pairs) gates scaling *that
treatment* and says nothing about how many systems the registry lists; it is unaffected
either way. The honest-coverage wording, the axis methodology, and the rule that cards
carry no rank are unchanged.

## Record

- Revoked clause: the geometric weekly activation rate, 21 July policy.
- Grounds: the rationale is unsupported as written; the cost of the alternative was
  measured on 2026-09-20 and is $0 and hours, not months.
- Retained: manifest-first publication, membership predicate, four weekly observations
  before publication, mechanical order, the schedule-not-verdict disclaimer.
- Effective: the first tranche run after the capacity dry run reports.

*Positive-only note: internal governance of this registry's own publication schedule.
No statement about any measured system is created, changed or withdrawn by this
amendment.*
