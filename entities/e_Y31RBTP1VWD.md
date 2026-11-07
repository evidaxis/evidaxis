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
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 50.0
  percentile: 40
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["github_commit_velocity"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.025024473179988835, "cohort_z": 1.439, "recent_weekly_commits": 58.1, "stars_not_scored": 4072}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.009821, "theil_sen": 0.009209, "cohort_z": -1.44, "latest": 86, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
note: "Title-matching OpenAlex record had author mismatch; treated as axis-2 absent."
---

# dora-rs

Evidaxis measures **dora-rs** on methodology m5. Momentum 50.0/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
