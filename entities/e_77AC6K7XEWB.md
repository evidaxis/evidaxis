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
  snapshot_id: d1eb0cec0f6a
  captured_at: 2026-10-31T03:43:22+00:00
  period: 2026-w44
  momentum: 51.0
  percentile: 54
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.03213161306304965, "cohort_z": 0.16, "recent_weekly_commits": 628.8, "stars_not_scored": 38308}
    openalex_citation_momentum: {"status": "insufficient", "slope": null, "cohort_z": null, "total_citations": 145, "by_year": {"2026": 132, "2025": 10, "2024": 3}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.028047, "theil_sen": 0.026648, "cohort_z": 0.0, "latest": 14, "points": 28, "points_reconstructable": 15, "as_of_partition": "2026-10-12", "unstable": false, "rising_vote": false}
note: "paper_ref: 2312.07104; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# SGLang

Evidaxis measures **SGLang** on methodology m5. Momentum 51.0/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
