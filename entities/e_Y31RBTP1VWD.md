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
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 58.4
  percentile: 87
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.03908631450972707, "cohort_z": 3.162, "recent_weekly_commits": 56.6, "stars_not_scored": 4001}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.010241, "theil_sen": 0.009524, "cohort_z": -1.811, "latest": 83, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "Title-matching OpenAlex record had author mismatch; treated as axis-2 absent."
---

# dora-rs

Evidaxis measures **dora-rs** on methodology m4. Momentum 58.4/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
