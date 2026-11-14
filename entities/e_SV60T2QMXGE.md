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
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 52.2
  percentile: 62
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.016489636021509223, "cohort_z": -0.179, "recent_weekly_commits": 35.5, "stars_not_scored": 60868}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.03011, "theil_sen": 0.028159, "cohort_z": 0.524, "latest": 375, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
note: "batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# CrewAI

Evidaxis measures **CrewAI** on methodology m5. Momentum 52.2/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
