# Pre-registration - system cards, template B against template A (2026-09-23)

> status: FIXED 2026-09-23, before template B is exposed on any production URL.
> Specification: second-brain `projects/bonsai/foundation/SPEC.md` v1.0 (run team-151).
> Code: branch `foundation-retrofit-cards` (commits 98781983, 8eb3a8a2, 35ce22eb).

## What changes

Template B answers the question a visitor arrives with (citations, commit activity,
dependents, stars, the niche) with measured numbers, each with source, date and the
niche median, on the first screen; the methodology mechanics (convergence gate,
cohort z-scores, percentile, derived signals) stay complete in a collapsed detail
block. Actions: download displayed values (CSV), JSON record, copy citation, follow
this system (per-system feed), report an error.

## Assignment

- A system card is in arm B when the index of the last character of its `entity_id`
  in `0123456789ABCDEFGHJKMNPQRSTVWXYZ` is even; otherwise arm A (unchanged template).
- The 48 URLs of the headline experiment (`web/src/data/canary-assignment.json`) are
  outside this assignment until that experiment's verdict (2026-10-31); afterwards
  they join by the same rule. Assignment is never changed after exposure.
- Arm A output is byte-identical to `main` before this change: 134 HTML pages and 134
  JSON twins compared in an identical build environment, 0 differences.

## Baseline (frozen now)

Search Console, 2026-08-26 to 2026-09-22, page dimension. Indexable cards outside the
headline experiment: 130 (B 61, A 69). Base impressions: B 151 on 33 pages, A 111 on
38 pages. Arms are unbalanced on status (watch B 6 / A 18) and axis count (two axes
B 14 / A 24); analysis is stratified for that reason, not re-assigned.

## Outcomes

- **Primary A (both arms, same definition):** impressions per page in the 14 days after
  exposure, each page normalised by its own baseline mean; stratified by status and
  number of measurable axes; reported per stratum and pooled.
- **Primary B (both arms, same definition):** share of engaged sessions (GA4) among
  sessions that land on a card from organic search.
- **Descriptive (arm B only):** `fnd_download`, `fnd_cite_copy`, `fnd_follow`,
  `fnd_report_error`, `fnd_tool_run` as absolute shares of B sessions. Arm A has no
  such actions by construction, so they are not compared across arms.
- **Secondary:** the frozen citation panel (readouts/CITATION-PANEL in the second
  brain) split by arm.

## What a verdict may claim

Only that template B changes the outcomes above on cards outside the headline
experiment by a stated amount within strata, over a stated window. It may not claim
the effect of any single block (blocks are not randomised within B), anything about
the 48 headline-experiment URLs, or anything about clicks (baseline: 1 click in 28
days). Without power the verdict is "no answer", not "no effect". New cards born on
2026-09-26 are an additional observation, aligned by days since indexable; calendar
and crawl differences are not removed by that alignment.

## Readings and worlds

T+7 (technical trace: indexability of both arms, events arriving, bots see numbers),
T+30 (after 2026-10-31, with the 48 URLs joined), T+90. World 1: B shows at least
1.3x impressions per page against A on the live cards within 14 days of exposure,
with power: template B becomes the template of all cards. World 2: below 1.3x with
power: B stays for its machine layer and actions; the impressions thesis moves to the
new cards at T+30.

## Stop-loss (rollback within one hour)

Build or `check-dist` failure; any byte change in arm A or the 48 shells; SEO audit
findings specific to B; 5xx; manual action in Search Console; loss of events; a
repeated defect in a stratified sample of at least 30 B cards (an empty card or
another system's numbers). Traffic is not a stop-loss.
