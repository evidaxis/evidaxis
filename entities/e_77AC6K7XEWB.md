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
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 53.1
  percentile: 69
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.039748776994893174, "cohort_z": 0.495, "recent_weekly_commits": 772.8, "stars_not_scored": 39138}
    openalex_citation_momentum: {"status": "present", "slope": 2.7423984667453274, "cohort_z": null, "total_citations": 2378, "by_year": {"2026": 1828, "2025": 481, "2024": 67, "2022": 1, "2017": 1}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.025799, "theil_sen": 0.024077, "cohort_z": 0.0, "latest": 16, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": false}
note: "paper_ref: 2312.07104; batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# SGLang

Evidaxis measures **SGLang** on methodology m5. Momentum 53.1/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
