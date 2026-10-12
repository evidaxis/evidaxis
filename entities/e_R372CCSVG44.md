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
  methodology_version: m4
  snapshot_id: ad5e404d4f82
  captured_at: 2026-10-12T12:11:36+00:00
  period: 2026-w41
  momentum: 41.7
  percentile: 23
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.02408545386851401, "cohort_z": 0.673, "recent_weekly_commits": 582.3, "stars_not_scored": 93625}
    openalex_citation_momentum: {"status": "present", "slope": 2.1570746061353976, "cohort_z": null, "total_citations": 1669, "by_year": {"2026": 904, "2025": 597, "2024": 161, "2023": 7}, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.006725, "theil_sen": 0.007042, "cohort_z": -2.003, "latest": 152, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "paper_ref: 2309.06180; incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# vLLM

Evidaxis measures **vLLM** on methodology m4. Momentum 41.7/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
