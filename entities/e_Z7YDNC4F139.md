---
schema_ver: 1.0
entity_id: e_Z7YDNC4F139
entity_type: repo
name: "llama.cpp"
slug: llama-cpp
homepage: "https://github.com/ggml-org/llama.cpp"
ids:
  github_repo: "ggml-org/llama.cpp"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ml-infrastructure
  sub_niche: llm-inference-serving
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 7bf8281671a3
  captured_at: 2026-11-28T03:40:51+00:00
  period: 2026-w48
  momentum: 60.0
  percentile: 92
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: ["deps_direct_dependents_momentum"]
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.03833603489523842, "cohort_z": 0.467, "recent_weekly_commits": 192.1, "stars_not_scored": 136453}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.025082, "theil_sen": 0.023489, "cohort_z": 1.131, "latest": 81, "points": 32, "points_reconstructable": 15, "as_of_partition": "2026-11-09", "unstable": false, "rising_vote": true}
note: "incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# llama.cpp

Evidaxis measures **llama.cpp** on methodology m5. Momentum 60.0/100; 2 axes present, 1 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
