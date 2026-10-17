---
schema_ver: 1.0
entity_id: e_FJPV9XH9GPR
entity_type: repo
name: "ms-swift"
slug: ms-swift
homepage: "https://swift.readthedocs.io"
ids:
  github_repo: "modelscope/ms-swift"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ml-infrastructure
  sub_niche: post-training-rl
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 4d9867e6f218
  captured_at: 2026-10-17T12:13:42+00:00
  period: 2026-w42
  momentum: 45.4
  percentile: 29
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.0043860588725610754, "cohort_z": -0.063, "recent_weekly_commits": 26.9, "stars_not_scored": 15868}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": -0.012264, "theil_sen": 0.0, "cohort_z": -0.674, "latest": 5, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "paper_ref: 2408.05517; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# ms-swift

Evidaxis measures **ms-swift** on methodology m5. Momentum 45.4/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
