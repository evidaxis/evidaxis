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
  methodology_version: m5
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 71.6
  percentile: 100
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: watch
  axes:
    github_commit_velocity: {"slope": 0.03024963501120268, "cohort_z": 0.513, "recent_weekly_commits": 80.5, "stars_not_scored": 14297}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.08181, "theil_sen": 0.078846, "cohort_z": 2.937, "latest": 50, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": false, "rising_vote": true}
note: "No canonical paper / paper has 0 citations indexed; axis-2 structurally absent."
---

# Microsoft Agent Framework

Evidaxis measures **Microsoft Agent Framework** on methodology m5. Momentum 71.6/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
