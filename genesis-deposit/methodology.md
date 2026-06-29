# Evidaxis Methodology v1 (m1)

Two axes, both computed from public data, within-cohort and robust:
- **Axis 1 — GitHub commit velocity:** log-slope of weekly commit counts (last 26 weeks); within-cohort robust-z (median/MAD), residualized on log stars. Stars are never scored.
- **Axis 2 — OpenAlex citation momentum:** log-slope of citations-per-year (partial current year dropped, earliest/birth year dropped when >=4 exist, >=3 completed years required); within-cohort robust-z, residualized on log total citations.

**Rising gate:** a system is Rising iff >=2 axes are present AND >=2 axes are rising. An axis is rising iff its raw slope > 0 AND its within-cohort z >= 0; commit-velocity additionally requires a minimum average weekly commit floor (a dormant repo is not rising). **Positive-only; there is no "worst" list.** Convergence over a sustained window cannot resolve at a single t=0 observation point, so an empty Rising tier at genesis is the expected output of the gate.

Genesis is a **hand-curated seed** (P5: first ~200 nodes seeded by hand), not a population sample. The seed manifest is the denominator; counts describe the seed, not AI. Canonical: https://evidaxis.org/methodology/v1/
