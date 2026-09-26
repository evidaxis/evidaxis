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
  methodology_version: m3
  snapshot_id: 9d2fe956adbc
  captured_at: 2026-09-26T22:11:54+00:00
  period: 2026-w39
  momentum: 56.0
  percentile: 67
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.015121070745072972, "cohort_z": 0.529, "recent_weekly_commits": 48.4, "stars_not_scored": 15344}
    openalex_citation_momentum: {"status": "present", "slope": 0.388710481154208, "cohort_z": -0.369, "total_citations": 4610, "by_year": {"2026": 352, "2025": 676, "2024": 610, "2023": 533, "2022": 400, "2021": 657, "2020": 611, "2019": 383, "2018": 226, "2017": 90, "2016": 30, "2015": 20, "2014": 12, "2013": 8, "2012": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.020578, "theil_sen": 0.020194, "cohort_z": 1.284, "latest": 207, "points": 23, "points_reconstructable": 15, "as_of_partition": "2026-09-07", "unstable": false, "rising_vote": true}
note: "Mature incumbent — included as cohort calibration; measured but not badge-eligible (P5 inclusion rule)."
---

# MuJoCo

Evidaxis measures **MuJoCo** on methodology m3. Momentum 56.0/100; 3 axes present, 1 axes converging.

This axis measures the frozen-panel trajectory of the package set selected and linkage-verified as of 2026-07-21. Systems outside that panel are not measured on this axis. Residual survivorship beyond the frozen universe is disclosed, not denied.
