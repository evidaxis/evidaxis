---
schema_ver: 1.0
entity_id: e_77AC6K7XEWB
entity_type: repo
name: "SGLang"
slug: sglang
homepage: "https://sglang.io"
ids:
  github_repo: "sgl-project/sglang"
  openalex_work_ids: ["W4415797413"]
classification:
  domain: ai
  industry: ml-infrastructure
  sub_niche: llm-inference-serving
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 4d9867e6f218
  captured_at: 2026-10-17T12:13:42+00:00
  period: 2026-w42
  momentum: 51.7
  percentile: 54
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.028678949921197853, "cohort_z": 0.158, "recent_weekly_commits": 565.8, "stars_not_scored": 37238}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 133, "by_year": {"2026": 120, "2025": 10, "2024": 3}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.029777, "theil_sen": 0.028881, "cohort_z": 0.116, "latest": 14, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "paper_ref: 2312.07104; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# SGLang

Evidaxis measures **SGLang** on methodology m5. Momentum 51.7/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
