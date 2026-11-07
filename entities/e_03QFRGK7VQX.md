---
schema_ver: 1.0
entity_id: e_03QFRGK7VQX
entity_type: repo
name: "MuJoCo"
slug: mujoco
homepage: "https://mujoco.org/"
ids:
  github_repo: "google-deepmind/mujoco"
  openalex_work_ids: ["W2158782408"]
classification:
  domain: ai
  industry: robotics
  sub_niche: embodied-ai
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 61.5
  percentile: 73
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.04604987695559766, "cohort_z": 1.864, "recent_weekly_commits": 93.0, "stars_not_scored": 16085}
    openalex_citation_momentum: {"status": "present", "slope": 0.39572634556155645, "cohort_z": -0.259, "total_citations": 4754, "by_year": {"2026": 470, "2025": 729, "2024": 669, "2023": 554, "2022": 433, "2021": 609, "2020": 561, "2019": 363, "2018": 211, "2017": 87, "2016": 27, "2015": 18, "2014": 12, "2013": 9, "2012": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.019936, "theil_sen": 0.019869, "cohort_z": 1.143, "latest": 236, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": true}
note: "Mature incumbent — included as cohort calibration; measured but not badge-eligible (P5 inclusion rule)."
---

# MuJoCo

Evidaxis measures **MuJoCo** on methodology m5. Momentum 61.5/100; 3 axes present, 2 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
