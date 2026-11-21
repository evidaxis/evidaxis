---
schema_ver: 1.0
entity_id: e_EY620A0EAK9
entity_type: repo
name: "Agno"
slug: agno
homepage: "https://agno.com"
ids:
  github_repo: "agno-agi/agno"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 63819f13c9c7
  captured_at: 2026-11-21T03:40:14+00:00
  period: 2026-w47
  momentum: 42.6
  percentile: 33
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.00828917119410546, "cohort_z": -0.522, "recent_weekly_commits": 35.1, "stars_not_scored": 43248}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.013114, "theil_sen": 0.012738, "cohort_z": -0.655, "latest": 122, "points": 31, "points_reconstructable": 15, "as_of_partition": "2026-11-02", "unstable": false, "rising_vote": false}
note: "batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# Agno

Evidaxis measures **Agno** on methodology m5. Momentum 42.6/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
