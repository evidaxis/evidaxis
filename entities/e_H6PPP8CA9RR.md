---
schema_ver: 1.0
entity_id: e_H6PPP8CA9RR
entity_type: repo
name: "LeRobot"
slug: lerobot
homepage: "https://github.com/huggingface/lerobot"
ids:
  github_repo: "huggingface/lerobot"
  openalex_work_ids: ["W7131910578"]
classification:
  domain: ai
  industry: robotics
  sub_niche: embodied-ai
score:  # DERIVED — never edited by hand; rebuilt from data each snapshot
  methodology_version: m5
  snapshot_id: 4d9867e6f218
  captured_at: 2026-10-17T12:13:42+00:00
  period: 2026-w42
  momentum: 44.4
  percentile: 20
  confidence: medium
  axes_present: ["github_commit_velocity", "deps_direct_dependents_momentum"]
  convergent_axes: []
  rising: false
  status: tracked
  axes:
    github_commit_velocity: {"slope": 0.004774296314616945, "cohort_z": -0.698, "recent_weekly_commits": 20.7, "stars_not_scored": 28243}
    openalex_citation_momentum: {"status": "absent", "slope": null, "cohort_z": null, "total_citations": 0, "by_year": null, "proxy": null}
    deps_direct_dependents_momentum: {"status": "scored", "slope": 0.018097, "theil_sen": 0.018961, "cohort_z": -0.195, "latest": 81, "points": 26, "points_reconstructable": 15, "as_of_partition": "2026-09-28", "unstable": false, "rising_vote": false}
note: "Paper exists but 0 citations indexed; axis-2 not yet usable."
---

# LeRobot

Evidaxis measures **LeRobot** on methodology m5. Momentum 44.4/100; 2 axes present, 0 axes converging.

This axis measures the trajectory of a system's own packages: declared in its own tree, published under that name, and not attributed by deps.dev to another repository. A package with no repository link is unverified and stays. The self-name exclusion list is fixed at the v2h.1 panel. Systems with no admitted package are not measured on this axis. Points that cannot be derived exactly are withheld, and the series restarts after a withheld point.
