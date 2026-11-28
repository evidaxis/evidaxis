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
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 32.5
  percentile: 6
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.04332194465155886, "cohort_z": -3.398, "recent_weekly_commits": 0.0, "stars_not_scored": 7166}
    openalex_citation_momentum: {"status": "present", "slope": 0.42561627353426584, "cohort_z": -0.808, "total_citations": 4650, "by_year": {"2026": 1245, "2025": 913, "2024": 676, "2023": 539, "2022": 433, "2021": 332, "2020": 262, "2019": 152, "2018": 81, "2017": 15, "2012": 2}, "proxy": "MoleculeNet (the standard DeepChem citation)"}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.003329, "theil_sen": 0.0, "cohort_z": 0.0, "latest": 8, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": true, "rising_vote": false}
---

# DeepChem

Evidaxis measures **DeepChem** on methodology m5. Momentum 32.5/100; 3 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
