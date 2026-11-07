---
schema_ver: 1.0
entity_id: e_1GSH6ZQHW7B
entity_type: repo
name: "Browser Use"
slug: browser-use
homepage: "https://github.com/browser-use/browser-use"
ids:
  github_repo: "browser-use/browser-use"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ai-agents
  sub_niche: gui-agents
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 39.9
  percentile: 33
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.05090453317967781, "cohort_z": -1.616, "recent_weekly_commits": 31.9, "stars_not_scored": 120218}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.008644, "theil_sen": 0.00859, "cohort_z": 0.0, "latest": 96, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# Browser Use

Evidaxis measures **Browser Use** on methodology m5. Momentum 39.9/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
