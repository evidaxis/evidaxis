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
  snapshot_id: a57effe0708b
  captured_at: 2026-10-04T02:32:12+00:00
  period: 2026-w40
  momentum: 53.3
  percentile: 47
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.008433261087241125, "cohort_z": 0.133, "recent_weekly_commits": 49.2, "stars_not_scored": 15449}
    openalex_citation_momentum: {"status": "present", "slope": 0.3891237548031822, "cohort_z": -0.379, "total_citations": 4550, "by_year": {"2026": 367, "2025": 677, "2024": 619, "2023": 524, "2022": 403, "2021": 635, "2020": 579, "2019": 365, "2018": 222, "2017": 88, "2016": 29, "2015": 20, "2014": 12, "2013": 8, "2012": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.020485, "theil_sen": 0.020204, "cohort_z": 1.046, "latest": 212, "points": 24, "points_reconstructable": 15, "as_of_partition": "2026-09-14", "unstable": false, "rising_vote": true}
note: "Mature incumbent — included as cohort calibration; measured but not badge-eligible (P5 inclusion rule)."
---

# MuJoCo

Evidaxis measures **MuJoCo** on methodology m3. Momentum 53.3/100; 3 axes present, 1 axes converging.

This axis measures the frozen-panel trajectory of the package set selected and linkage-verified as of 2026-07-21. Systems outside that panel are not measured on this axis. Residual survivorship beyond the frozen universe is disclosed, not denied.
