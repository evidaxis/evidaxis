---
schema_ver: 1.0
entity_id: e_A4CCB1NFPZB
entity_type: repo
name: "UI-TARS Desktop"
slug: ui-tars-desktop
homepage: "https://github.com/bytedance/UI-TARS-desktop"
ids:
  github_repo: "bytedance/UI-TARS-desktop"
  openalex_work_ids: ["W4406755521"]
classification:
  domain: ai
  industry: ai-agents
  sub_niche: gui-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 59.0
  percentile: 67
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.007963375418791357, "cohort_z": 1.432, "recent_weekly_commits": 0.7, "stars_not_scored": 39564}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 119, "by_year": {"2026": 87, "2025": 32}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.005073, "theil_sen": 0.003356, "cohort_z": 0.0, "latest": 76, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
---

# UI-TARS Desktop

Evidaxis measures **UI-TARS Desktop** on methodology m5. Momentum 59.0/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
