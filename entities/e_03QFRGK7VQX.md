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
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 57.7
  percentile: 73
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.04191357755381195, "cohort_z": 1.445, "recent_weekly_commits": 99.7, "stars_not_scored": 18543}
    openalex_citation_momentum: {"status": "present", "slope": 0.4537829743000968, "cohort_z": -0.857, "total_citations": 9070, "by_year": {"2026": 2294, "2025": 1581, "2024": 1239, "2023": 990, "2022": 780, "2021": 709, "2020": 610, "2019": 388, "2018": 281, "2017": 121, "2016": 33, "2015": 20, "2014": 15, "2013": 7, "2012": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.020204, "theil_sen": 0.020177, "cohort_z": 1.257, "latest": 251, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": true}
note: "Mature incumbent — included as cohort calibration; measured but not badge-eligible (P5 inclusion rule)."
---

# MuJoCo

Evidaxis measures **MuJoCo** on methodology m5. Momentum 57.7/100; 3 axes present, 2 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
