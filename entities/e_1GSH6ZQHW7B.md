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
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 47.9
  percentile: 17
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": -0.0003924380856558141, "cohort_z": -0.329, "recent_weekly_commits": 40.3, "stars_not_scored": 118986}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.008832, "theil_sen": 0.008838, "cohort_z": 0.0, "latest": 95, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": false, "rising_vote": false}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# Browser Use

Evidaxis measures **Browser Use** on methodology m5. Momentum 47.9/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
