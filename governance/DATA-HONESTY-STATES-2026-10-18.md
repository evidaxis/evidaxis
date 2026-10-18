# Data honesty: observation states, 2026-10-18

This is a presentation correction, not a methodology or calculation change.
The latest snapshot's membership and its recorded collection evidence determine
the observation state independently of the last measured values:

- `measured`: an observation exists in the latest snapshot.
- `observation_skipped`: the latest dropped.json declares a collection gap.
  GitHub statistics were not ready; the next attempt is the next weekly snapshot.
- `departure_confirmed`: dated departure evidence records a repository gone or a
  repository name resolving to a different repository ID. Earlier departure
  evidence remains applicable until a later measurement. Only this state uses
  the preserved-record label `superseded`.
- `absence_unexplained`: absent without either kind of evidence. The public text
  states the absence neutrally, without inferring a departure.

Each existing record retains its last measured values, their dates, methodology,
snapshot identity and citation. A declared gap without any earlier measurement
does not acquire fabricated values or an invented historical card. Raw departure
and gap evidence is used internally; it does not bypass the person-free public
projection or owner-transition masking.

The model supplies Card B HTML, entity JSON, values/history CSV and system feeds.
Template A HTML remains byte-frozen through 2026-10-31; its state is corrected in
JSON now and its HTML correction is deferred until 2026-11-01. Indexing policy,
canary assignment and control-shell semantics are unchanged.

The main site feed contains growth and neutral milestones only. Threshold-loss
events remain in complete event JSON and individual system feeds. Filtering
occurs before the existing 100-entry limit. This strengthens positive-only
discovery under Constitution invariant 2; it does not erase historical events.
Published collection-event titles and summaries retain their original identity;
the new observation explanation is an annotation in their state metadata.

Weekly direct dependents and daily package dependents retain separate labels,
sources, dates, package scopes and scoring roles. The weekly union is the axis
input; the daily REST count is unscored context for one pinned package. Neither
substitutes for the other. Current weekly admission can include packages with no
repository metadata; these are unverified, as stated in methodology m4 section 1.
No uniform verification claim is made for that union. Older methodology
definitions remain unchanged.

The deployment receipt compares snapshot date, methodology version, snapshot ID,
entity count and a deterministic entity's recorded development-axis value from
the built snapshot with the live snapshot. The built controls are also checked
against the canonical collected snapshot. Retry counts and intervals are unchanged.

No archive bytes, ETL files, historical governance records, thresholds, axes,
scores, package admission rules, schedules, styles, layouts or sitemap policies
are changed. Constitution invariants 1 and 4 continue to apply: systems only,
and an append-only archive whose captured facts remain addressable.
