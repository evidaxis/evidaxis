---
schema_ver: 1.0
entity_id: e_TRJN6D7V12H
entity_type: repo
name: "Ollama"
slug: ollama
homepage: "https://ollama.com"
ids:
  github_repo: "ollama/ollama"
  openalex_work_ids: []
classification:
  domain: ai
  industry: ml-infrastructure
  sub_niche: llm-inference-serving
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 04724603bccf
  captured_at: 2026-11-14T03:45:26+00:00
  period: 2026-w46
  momentum: 49.5
  percentile: 46
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.01951464675682011, "cohort_z": -0.305, "recent_weekly_commits": 25.2, "stars_not_scored": 186903}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.011077, "theil_sen": 0.010888, "cohort_z": 0.23, "latest": 1117, "points": 30, "points_reconstructable": 15, "as_of_partition": "2026-10-26", "unstable": false, "rising_vote": false}
note: "batch#01 2026-07-01 (taxonomy v1, provisional, not-yet-deployed)"
---

# Ollama

Evidaxis measures **Ollama** on methodology m5. Momentum 49.5/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
