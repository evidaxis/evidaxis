-- Read-only pull behind the frozen-panel equivalence replay of the 2026-09-14 verdict.
-- Question: which direct, highest-release dependents at the four drift partitions are
-- post-freeze panel packages? Those are exactly the dependents the drifted self-name
-- exclusion list could have removed from frozen systems' counts (name variants included
-- as a superset; collectors/replay_axis3_v2h1_frozen_panel.py matches exact strings).
SELECT DISTINCT
  FORMAT_DATE("%F", DATE(d.SnapshotAt)) AS snap,
  d.System AS sys,
  d.Name AS name,
  d.Dependent.System AS dep_sys,
  d.Dependent.Name AS dep_name
FROM `bigquery-public-data.deps_dev_v1.Dependents` AS d
WHERE DATE(d.SnapshotAt) IN ("2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31")
  AND d.MinimumDepth = 1
  AND d.DependentIsHighestReleaseWithResolution
  AND d.Dependent.System IN ("PYPI", "NPM")
  AND d.Dependent.Name IN ("langchain", "freetoken", "nnunet", "nnUNet", "ultralytics",
                           "transformers", "firecrawl", "firecrawl-py", "crawl4ai",
                           "claude-mem", "paddleocr", "gpt4all", "gpt4free", "g4f",
                           "scikit-learn", "keras")
