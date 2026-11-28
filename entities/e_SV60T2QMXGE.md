---
schema_ver: 1.0
entity_id: e_SV60T2QMXGE
entity_type: repo
name: "CrewAI"
slug: crewai
homepage: "https://crewai.com"
ids:
  github_repo: "crewAIInc/crewAI"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ai-agents
  sub_niche: agent-frameworks
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 52.8
  percentile: 60
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.020820779419651193, "cohort_z": -0.054, "recent_weekly_commits": 38.5, "stars_not_scored": 61331}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.028705, "theil_sen": 0.026793, "cohort_z": 0.497, "latest": 386, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
note: "batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# CrewAI

Evidaxis measures **CrewAI** on methodology m5. Momentum 52.8/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
