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
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 57.9
  percentile: 67
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.03643225750860096, "cohort_z": 0.92, "recent_weekly_commits": 91.4, "stars_not_scored": 17879}
    openalex_citation_momentum: {"status": "present", "slope": 0.4118222751785598, "cohort_z": -0.215, "total_citations": 5612, "by_year": {"2026": 888, "2025": 895, "2024": 785, "2023": 640, "2022": 483, "2021": 619, "2020": 565, "2019": 366, "2018": 215, "2017": 88, "2016": 27, "2015": 18, "2014": 12, "2013": 9, "2012": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.02007, "theil_sen": 0.020016, "cohort_z": 1.182, "latest": 244, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": true}
note: "Mature incumbent — included as cohort calibration; measured but not badge-eligible (P5 inclusion rule)."
---

# MuJoCo

Evidaxis measures **MuJoCo** on methodology m5. Momentum 57.9/100; 3 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
