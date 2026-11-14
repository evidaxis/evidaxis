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
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 49.9
  percentile: 50
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.004842453578471469, "cohort_z": -0.022, "recent_weekly_commits": 0.7, "stars_not_scored": 39600}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 830, "by_year": {"2026": 558, "2025": 266, "2024": 6}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.004834, "theil_sen": 0.003268, "cohort_z": 0.0, "latest": 76, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
---

# UI-TARS Desktop

Evidaxis measures **UI-TARS Desktop** on methodology m5. Momentum 49.9/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
