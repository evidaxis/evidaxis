/**
 * Glossary vocabulary. Two sections, reading order preserved:
 *  1. Terms on every page: plain wording for the words people meet on cards,
 *     hubs and the home page (explicit, stable anchor ids).
 *  2. How a figure is computed: the methodology terms. Their text is unchanged
 *     and their anchors stay derived from the name, as before, so existing
 *     links keep resolving.
 */
export type GlossaryTerm = { id: string; name: string; def: string };

export const glossarySlug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

export const PLAIN_TERMS: GlossaryTerm[] = [
  { id: 'system', name: 'System', def: 'One open AI project that Evidaxis measures: a code repository, a model or a tool, kept under one record with a stable id. Evidaxis measures systems, never people.' },
  { id: 'niche', name: 'Niche', def: 'A group of systems that do the same job, such as Coding Agents. Every comparison on the site (niche median, niche medal, Rising) is made inside one niche.' },
  { id: 'field', name: 'Field', def: 'A group of related niches, such as AI Agents. A field page lists its niches side by side; it never merges their systems into one list.' },
  { id: 'not-yet-assigned', name: 'Not yet assigned', def: 'A system that is measured every week but has no niche yet. Until a niche is assigned it has no niche median, no medal and no niche Rising comparison; its own figures are still shown.' },
  { id: 'weekly-snapshot', name: 'Snapshot', def: 'The weekly, dated record of every measurement, frozen on its date and released under CC0. Every figure on the site belongs to one snapshot, named by its week and date.' },
  { id: 'commits-per-week', name: 'Commits per week', def: 'The average number of commits per week to the system’s GitHub repository over the trailing 12 weeks, from GitHub’s weekly commit activity.' },
  { id: 'citation', name: 'Citation', def: 'A work in OpenAlex that cites the system’s paper. The count is all citing works indexed to date, all years including the current one. A system with no linked paper has no citation count.' },
  { id: 'verified-direct-dependent', name: 'Verified direct dependent', def: 'A package that depends directly on the system’s package, counted by deps.dev. Evidaxis shows the figure only for packages whose identity is verified as the system’s own; when the trend is not scored yet, the figure is a count only.' },
  { id: 'star', name: 'Star', def: 'The GitHub stargazer count. Evidaxis records it and shows it, but never scores it: size is not momentum.' },
  { id: 'not-measured-count-only', name: 'Not measured / count only', def: 'Not measured: there is no reading for this measure, for example no paper is linked or the package is outside the panel. Count only: the count was measured, but there is not yet enough history or coverage to score its trend; the number is still shown.' },
  { id: 'niche-median', name: 'Niche median', def: 'The middle value of one measure among the systems in a niche that have that measure. Systems without the measure are left out, not counted as zero.' },
  { id: 'niche-medal', name: 'Niche medal', def: 'A medal for a system whose citations or verified dependents reach 2×, 10× or 100× its niche median: bronze, silver or gold. The badge shows the multiple and the measure; it is a threshold, not a place.' },
  { id: 'niche-rising', name: 'Rising', def: 'At least two of the three measures (commits per week, citations, verified dependents) are rising together in the system’s niche on this snapshot. It describes the recorded series; it is not a forecast.' },
];

// Section 2: the methodology vocabulary, text unchanged.
const computed: { name: string; def: string }[] = [
  { name: 'Momentum', def: 'The slope of a system’s public signals over time: how fast it is moving. Evidaxis scores that slope and nothing else. A repository with two million stars and a flat curve scores zero.' },
  { name: 'Momentum Score', def: 'A 0–100 readout that maps a system’s within-cohort axis z-scores onto a single number within a cohort, collapsed to one number. A convenience view only. Recognition is decided by the convergence gate, never by this number.' },
  { name: 'Development velocity', def: 'Axis 1: the least-squares slope of log(1 + weekly commits) over the trailing 26 weeks. A fast, leading signal of where active work is accelerating.' },
  { name: 'Citation momentum', def: 'Axis 2: the slope of log(1 + citations per year) to a system’s canonical paper (OpenAlex). A slow, confirming signal of scholarly acceleration. Three rules keep it honest: drop the partial current year, drop the birth year once four full years exist, and require at least three completed years.' },
  { name: 'Direct-dependents momentum', def: 'Axis 3 in m3: the log-slope of unique direct dependents over each frozen-panel package union, using confirmed-clean deps.dev weekly partitions. Residualize slope on log(1 + latest), then robust z within cohort. At least 14 clean points and 5 latest dependents are required; cohort agreement and fragility can withhold a vote.' },
  { name: 'Within-cohort robust-z', def: 'Normalization: a raw axis slope is converted to a z-score using the median and median absolute deviation of its cohort (resistant to a single outlier), so "rising" means rising relative to peers, not in absolute terms.' },
  { name: 'Residualization', def: 'Axes 1 and 2 adjust their robust z against size proxies (log stars and log total citations). Axis 3 in m3 residualizes raw slope against log(1 + latest dependents) before robust z. This removes the fitted size relationship within each cohort.' },
  { name: 'Convergence Gate', def: 'The recognition rule in m2 and m3: a non-incumbent system is Rising only when its cohort has at least five members and at least two independent axes are present and rising (positive slope and within-cohort z at least one, plus axis-specific floors and vetoes). M2 has two axes; m3 accepts any two of three.' },
  { name: 'Rising', def: 'Status: two or more independent axes converge upward within the cohort. The full badge, and the rare one. It fires only when two separate signals agree, so a single pushed number cannot earn it.' },
  { name: 'Watch', def: 'Status: exactly one axis is rising; a second independent axis has not yet converged. A candidate signal, not a badge.' },
  { name: 'Tracked', def: 'Status: measured on two or more axes, none currently rising relative to the cohort.' },
  { name: 'Single-axis', def: 'Status used when fewer than two axes are available and no other status rule applies. The convergence gate needs at least two measured axes under the record\'s methodology version.' },
  { name: 'Calibration', def: 'Status: a mature incumbent included to anchor a cohort’s statistics. Measured but never badge-eligible: the badges go to systems on the rise.' },
  { name: 'Cohort', def: 'A peer set (a sub-niche within an industry) against which a system’s momentum is normalized. Membership controls the z-scoring, so a human draws the cohort line by hand.' },
  { name: 'Snapshot', def: 'A frozen, dated, hash-verified record of every measurement at a point in time, released under CC0. You cannot back-fill a baseline after the flare. The snapshot series is the part that compounds: a longitudinal map that no one can reconstruct from scratch later.' },
  { name: 'Score receipt', def: 'Three fields ride with every published number: methodology version, snapshot id, and manifest hash. With them, any score is independently checkable against its hash-pinned inputs in the public CC0 data.' },
];
export const COMPUTED_TERMS: GlossaryTerm[] = computed.map((t) => ({ id: glossarySlug(t.name), ...t }));

export const GLOSSARY_SECTIONS = [
  { id: 'terms-on-every-page', title: 'Terms on every page', terms: PLAIN_TERMS },
  { id: 'how-a-figure-is-computed', title: 'How a figure is computed', terms: COMPUTED_TERMS },
] as const;
export const ALL_TERMS: GlossaryTerm[] = [...PLAIN_TERMS, ...COMPUTED_TERMS];

/** Anchor href for a plain term, e.g. glossaryHref('niche-medal'). Throws on unknown ids. */
export function glossaryHref(id: string): string {
  if (!ALL_TERMS.some((t) => t.id === id)) throw new Error(`Unknown glossary anchor: ${id}`);
  return `/glossary/#${id}`;
}
