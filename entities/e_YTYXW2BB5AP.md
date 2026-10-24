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
  methodology_version: m5
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 33.6
  percentile: 22
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.010726520750554289, "cohort_z": -2.898, "recent_weekly_commits": 0.5, "stars_not_scored": 7081}
    openalex_citation_momentum: {"status": "present", "slope": 0.3818277799356383, "cohort_z": -1.027, "total_citations": 3093, "by_year": {"2026": 542, "2025": 559, "2024": 484, "2023": 387, "2022": 328, "2021": 309, "2020": 252, "2019": 145, "2018": 73, "2017": 12, "2012": 2}, "proxy": "MoleculeNet (the standard DeepChem citation)"}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.005047, "theil_sen": 0.0, "cohort_z": 0.0, "latest": 8, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": true, "rising_vote": false}
---

# DeepChem

Evidaxis measures **DeepChem** on methodology m5. Momentum 33.6/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
