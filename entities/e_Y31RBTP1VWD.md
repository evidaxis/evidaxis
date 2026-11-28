---
schema_ver: 1.0
entity_id: e_Y31RBTP1VWD
entity_type: repo
name: "dora-rs"
slug: dora-rs
homepage: "https://github.com/dora-rs/dora"
ids:
  github_repo: "dora-rs/dora"
  openalex_work_ids: ["W7129446322"]
classification:
  domain: ai
  industry: robotics
  sub_niche: embodied-ai
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 45.1
  percentile: 20
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.008670247541189877, "cohort_z": 0.401, "recent_weekly_commits": 54.6, "stars_not_scored": 4111}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 1, "by_year": {"2026": 1}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.009299, "theil_sen": 0.008643, "cohort_z": -1.187, "latest": 86, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
note: "Title-matching OpenAlex record had author mismatch; treated as axis-2 absent."
---

# dora-rs

Evidaxis measures **dora-rs** on methodology m5. Momentum 45.1/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
