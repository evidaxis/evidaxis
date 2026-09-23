// Chart conclusions are versioned templates, never per-entity prose.
export const CHART_COPY = {
  commits_ratio: '{name} averaged {value} commits a week, {ratio} times the niche median of {median}.',
  commits: '{name} averaged {value} commits a week; niche median {median}.',
  commits_zero: '{name} recorded 0 commits a week over the last {zero_weeks} captured weeks; niche median {median}.',
  commits_missing: 'No commit reading for {name}; niche median {median}.',
  heatmap: '{active} of the last {weeks} captured weeks had commits for {name}.',
  citations: '{value} OpenAlex citing works for {name}; niche median {median}.',
  dependents: '{value} direct dependents on deps.dev for {name}; niche median {median}.',
  daily: '{name} recorded {value} daily dependents (unscored); daily niche median not measured.',
  backfill: '{name} has {value} reconstructed commits in the latest week; reconstructed niche median not measured.',
  niche: '{name} at {value} commits a week among {systems} systems; niche median {median}.',
  changes: '{count} published values changed for {name} since {previous}.',
  no_numeric_change: 'No numeric change since {previous} for {name}.',
  first: 'First observation {date} for {name}; {count} measured values.',
};
