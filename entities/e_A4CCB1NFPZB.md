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
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 49.7
  percentile: 33
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.005472838354665336, "cohort_z": -0.055, "recent_weekly_commits": 0.7, "stars_not_scored": 39597}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 963, "by_year": {"2026": 698, "2025": 260, "2024": 5}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.004472, "theil_sen": 0.002844, "cohort_z": 0.0, "latest": 77, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
---

# UI-TARS Desktop

Evidaxis measures **UI-TARS Desktop** on methodology m5. Momentum 49.7/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
