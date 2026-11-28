---
schema_ver: 1.0
entity_id: e_B1Q69HZTTMA
entity_type: repo
name: "TRL"
slug: trl
homepage: "https://huggingface.co/docs/trl"
ids:
  github_repo: "huggingface/trl"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ml-infrastructure
  sub_niche: post-training-rl
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 53.1
  percentile: 64
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.030502996795495677, "cohort_z": 0.5, "recent_weekly_commits": 72.0, "stars_not_scored": 19847}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.008618, "theil_sen": 0.007129, "cohort_z": 0.0, "latest": 160, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
note: "paper_ref: 2402.03300; incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# TRL

Evidaxis measures **TRL** on methodology m5. Momentum 53.1/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
