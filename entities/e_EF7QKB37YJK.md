---
schema_ver: 1.0
entity_id: e_EF7QKB37YJK
entity_type: repo
name: "SWE-bench"
slug: swe-bench
homepage: "https://www.swebench.com"
ids:
  github_repo: "SWE-bench/SWE-bench"
  openalex_work_ids: []
classification:
  domain: ai
  industry: developer-tools
  sub_niche: coding-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 57.4
  percentile: 74
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.033533051342160294, "cohort_z": 1.188, "recent_weekly_commits": 8.0, "stars_not_scored": 6007}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.018348, "theil_sen": 0.016824, "cohort_z": 0.0, "latest": 6, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "paper_ref: 2310.06770; incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# SWE-bench

Evidaxis measures **SWE-bench** on methodology m4. Momentum 57.4/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
