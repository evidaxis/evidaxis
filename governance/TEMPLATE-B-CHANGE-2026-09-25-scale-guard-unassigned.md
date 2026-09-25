# Template B change during the observation window: systems without a niche, scale guard (2026-09-25)

> status: FIXED 2026-09-25, recorded before the change reaches production and before the
> 2026-09-26 snapshot admits the queued systems.
> Relates to: FOUNDATION-RETROFIT-CARDS-PREREG-2026-09-23.md and its addendum;
> REGISTRY-GROWTH-POLICY-2026-07-21.md (non-gating taxonomy: unassigned bucket).

## Why
The 2026-09-26 snapshot admits 5,705 queued systems, all in `unassigned-v1`, with GitHub
data only. A scale simulation on a synthetic snapshot of 5,917 systems built 9.27 GB with
2,899 HTML pages above 1 MB: every card B of an unassigned system listed all cohort peers.

## What changes
- Arm B cards of systems in `unassigned-v1` (about 38 today): the bucket is not a niche,
  so these cards no longer show niche medians, niche chart bands, a niche section or a peer
  table; they say "Niche: not yet assigned." Cards of systems in real niches are unchanged
  (0 changed pages in the comparison build).
- Card B peer tables are capped at 50 rows with a link to the niche hub (no real niche
  exceeds 19 members today, so no current card changes).
- Lists above 250 rows paginate at 200 per page (cohort hubs, coverage, snapshot pages);
  lists at or below 250 rows render byte-identically. The home catalog lists systems with
  an assigned niche and links to the unassigned list. Site-wide feeds keep the latest 100
  items. Niche medals are not computed for `unassigned-v1`.
- Result on the same simulation: 875 MB, 144 MB as a deploy archive, no HTML page above 1 MB.

## What does not change
- Arm A output and the 48 headline-experiment shells: byte-identical (clean builds compared).
- Assignment, baseline, outcome definitions, strata and readings of the pre-registration.

## Effect on the reading
- The unassigned B cards lose comparisons that were not niche comparisons; they are a
  stratum readers of T+7 and T+30 can separate by cohort. New cards born on 2026-09-26 are
  rendered with this rule from their first day.
