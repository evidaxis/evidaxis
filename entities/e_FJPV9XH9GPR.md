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
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 44.6
  percentile: 27
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.0044754853881686565, "cohort_z": -0.195, "recent_weekly_commits": 26.8, "stars_not_scored": 15922}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": -0.010492, "theil_sen": 0.0, "cohort_z": -0.674, "latest": 5, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": false, "rising_vote": false}
note: "paper_ref: 2408.05517; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# ms-swift

Evidaxis measures **ms-swift** on methodology m5. Momentum 44.6/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
