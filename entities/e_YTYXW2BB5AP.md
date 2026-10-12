---
schema_ver: 1.0
entity_id: e_YTYXW2BB5AP
entity_type: repo
name: "DeepChem"
slug: deepchem
homepage: "https://deepchem.io/"
ids:
  github_repo: "deepchem/deepchem"
  openalex_work_ids: ["W2594183968"]
classification:
  domain: ai
  industry: ai-for-science
  sub_niche: drug-discovery
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 40.1
  percentile: 22
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.004207435970353374, "cohort_z": -1.659, "recent_weekly_commits": 0.5, "stars_not_scored": 7051}
    openalex_citation_momentum: {"status": "present", "slope": 0.43365163524794526, "cohort_z": -0.728, "total_citations": 3064, "by_year": {"2026": 503, "2025": 555, "2024": 483, "2023": 391, "2022": 331, "2021": 318, "2020": 257, "2019": 148, "2018": 71, "2017": 5, "2012": 2}, "proxy": "MoleculeNet (the standard DeepChem citation)"}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.005541, "theil_sen": 0.0, "cohort_z": 0.0, "latest": 8, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": true, "rising_vote": false}
---

# DeepChem

Evidaxis measures **DeepChem** on methodology m4. Momentum 40.1/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
