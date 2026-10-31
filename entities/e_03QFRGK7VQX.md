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
  snapshot_id: d1eb0cec0f6a
  captured_at: 2026-10-31T03:43:22+00:00
  period: 2026-w44
  momentum: 56.4
  percentile: 80
  confidence: medium
  axes_present: ["github_commit_velocity", "openalex_citation_momentum", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.035285419127658216, "cohort_z": 0.74, "recent_weekly_commits": 78.7, "stars_not_scored": 15981}
    openalex_citation_momentum: {"status": "present", "slope": 0.3999477287428289, "cohort_z": -0.358, "total_citations": 4632, "by_year": {"2026": 430, "2025": 721, "2024": 666, "2023": 554, "2022": 428, "2021": 607, "2020": 539, "2019": 330, "2018": 208, "2017": 84, "2016": 25, "2015": 18, "2014": 12, "2013": 8, "2012": 2}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.019875, "theil_sen": 0.019758, "cohort_z": 1.152, "latest": 229, "points": 28, "points_reconstructable": 15, "as_of_partition": "2026-10-12", "unstable": false, "rising_vote": true}
note: "Mature incumbent — included as cohort calibration; measured but not badge-eligible (P5 inclusion rule)."
---

# MuJoCo

Evidaxis measures **MuJoCo** on methodology m5. Momentum 56.4/100; 3 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
