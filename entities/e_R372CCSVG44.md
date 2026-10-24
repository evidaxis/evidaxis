---
schema_ver: 1.0
entity_id: e_R372CCSVG44
entity_type: repo
name: "vLLM"
slug: vllm
homepage: "https://vllm.ai"
ids:
  github_repo: "vllm-project/vllm"
  openalex_work_ids: ["W4387321091"]
classification:
  domain: ai
  industry: ml-infrastructure
  sub_niche: llm-inference-serving
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 9a3f0a2522ac
  captured_at: 2026-10-24T03:35:10+00:00
  period: 2026-w43
  momentum: 40.7
  percentile: 31
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.04646479530182762, "cohort_z": 0.543, "recent_weekly_commits": 682.7, "stars_not_scored": 95256}
    openalex_citation_momentum: {"status": "present", "slope": 2.1194628955166044, "cohort_z": null, "total_citations": 1771, "by_year": {"2026": 971, "2025": 623, "2024": 169, "2023": 8}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.006287, "theil_sen": 0.006557, "cohort_z": -2.024, "latest": 155, "points": 27, "points_reconstructable": 15, "as_of_partition": "2026-10-05", "unstable": false, "rising_vote": false}
note: "paper_ref: 2309.06180; incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# vLLM

Evidaxis measures **vLLM** on methodology m5. Momentum 40.7/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
