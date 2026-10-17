---
schema_ver: 1.0
entity_id: e_KRDEF79H7GD
entity_type: product
name: "Zed"
slug: zed
homepage: "https://zed.dev"
ids:
  github_repo: "zed-industries/zed"
  openalex_work_ids: []
classification:
  domain: ai
  industry: developer-tools
  sub_niche: coding-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 4d9867e6f218
  captured_at: 2026-10-17T12:13:42+00:00
  period: 2026-w42
  momentum: 47.4
  percentile: 26
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": -0.025417674027372786, "cohort_z": 0.254, "recent_weekly_commits": 125.8, "stars_not_scored": 91840}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.008916, "theil_sen": 0.007251, "cohort_z": -0.674, "latest": 13, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# Zed

Evidaxis measures **Zed** on methodology m5. Momentum 47.4/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
