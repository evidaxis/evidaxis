---
schema_ver: 1.0
entity_id: e_M5SCCQPBZ89
entity_type: repo
name: "Microsoft Agent Framework"
slug: microsoft-agent-framework
homepage: "https://github.com/microsoft/agent-framework"
ids:
  github_repo: "microsoft/agent-framework"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 68.4
  percentile: 93
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.0175679004799151, "cohort_z": 0.602, "recent_weekly_commits": 71.7, "stars_not_scored": 14074}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.078227, "theil_sen": 0.077027, "cohort_z": 2.34, "latest": 26, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": true}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# Microsoft Agent Framework

Evidaxis measures **Microsoft Agent Framework** on methodology m4. Momentum 68.4/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
