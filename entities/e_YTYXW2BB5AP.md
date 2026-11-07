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
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 31.5
  percentile: 11
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.023764690310956113, "cohort_z": -3.203, "recent_weekly_commits": 0.2, "stars_not_scored": 7127}
    openalex_citation_momentum: {"status": "present", "slope": 0.37425419556026107, "cohort_z": -1.235, "total_citations": 3203, "by_year": {"2026": 671, "2025": 568, "2024": 485, "2023": 381, "2022": 325, "2021": 295, "2020": 247, "2019": 143, "2018": 72, "2017": 14, "2012": 2}, "proxy": "MoleculeNet (the standard DeepChem citation)"}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.004233, "theil_sen": 0.0, "cohort_z": 0.0, "latest": 8, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": true, "rising_vote": false}
---

# DeepChem

Evidaxis measures **DeepChem** on methodology m5. Momentum 31.5/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
