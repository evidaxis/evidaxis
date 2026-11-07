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
  snapshot_id: 868e3c39d9c7
  captured_at: 2026-11-07T03:43:55+00:00
  period: 2026-w45
  momentum: 54.9
  percentile: 77
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: calibration
  axes:
    github_commit_velocity: {"slope": 0.022928440031124864, "cohort_z": 0.009, "recent_weekly_commits": 162.9, "stars_not_scored": 133585}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.026075, "theil_sen": 0.02452, "cohort_z": 0.774, "latest": 78, "points": 29, "points_reconstructable": 15, "as_of_partition": "2026-10-19", "unstable": false, "rising_vote": false}
note: "incumbent (calibration); batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# llama.cpp

Evidaxis measures **llama.cpp** on methodology m5. Momentum 54.9/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
